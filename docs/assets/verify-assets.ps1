[CmdletBinding()]
param(
    [string]$RepoRoot
)

$ErrorActionPreference = 'Stop'
if ([string]::IsNullOrWhiteSpace($RepoRoot)) {
    $RepoRoot = Join-Path $PSScriptRoot '..\..'
}
$repo = (Resolve-Path -LiteralPath $RepoRoot).Path.TrimEnd([char[]]'\/')
$manifestPath = Join-Path $repo 'docs\assets\asset-manifest.json'
$ledgerPath = Join-Path $repo 'docs\assets\asset-ledger.csv'
$attributionPath = Join-Path $repo 'docs\assets\THIRD_PARTY_ASSETS.md'

if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) {
    throw "Asset manifest not found: $manifestPath"
}

$manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
if ($manifest.schemaVersion -ne 1) {
    throw "Unsupported asset manifest schemaVersion: $($manifest.schemaVersion)"
}

$extensions = @($manifest.scope.assetExtensions | ForEach-Object { $_.ToLowerInvariant() })
$records = @($manifest.assets)
$discovered = @()

foreach ($relativeRoot in @($manifest.scope.scanRoots)) {
    $root = Join-Path $repo ($relativeRoot -replace '/', '\')
    if (-not (Test-Path -LiteralPath $root -PathType Container)) {
        continue
    }

    $discovered += Get-ChildItem -LiteralPath $root -Recurse -File | Where-Object {
        $extensions -contains $_.Extension.ToLowerInvariant()
    } | ForEach-Object {
        $_.FullName.Substring($repo.Length).TrimStart([char[]]'\/').Replace('\', '/')
    }
}

$errors = [System.Collections.Generic.List[string]]::new()
$recordIds = @($records | ForEach-Object { $_.internalAssetId })
$recordFiles = @($records | ForEach-Object { $_.filename })

foreach ($duplicate in @($recordIds | Group-Object | Where-Object Count -gt 1)) {
    $errors.Add("Duplicate internalAssetId: $($duplicate.Name)")
}
foreach ($duplicate in @($recordFiles | Group-Object | Where-Object Count -gt 1)) {
    $errors.Add("Duplicate asset filename: $($duplicate.Name)")
}
foreach ($file in @($discovered | Where-Object { $recordFiles -notcontains $_ })) {
    $errors.Add("Shipped visual file is absent from manifest: $file")
}
foreach ($file in @($recordFiles | Where-Object { $discovered -notcontains $_ })) {
    $errors.Add("Manifest asset is missing from a scanned root: $file")
}

$approvedLicenses = @($manifest.policy.approvedLicenseIds)
$caseByCase = @($manifest.policy.caseByCaseLicenseReviewRequired)
$attributionText = Get-Content -LiteralPath $attributionPath -Raw
$ledgerRows = if (Test-Path -LiteralPath $ledgerPath -PathType Leaf) { @(Import-Csv -LiteralPath $ledgerPath) } else { @() }

foreach ($record in $records) {
    $required = @(
        'internalAssetId', 'filename', 'assetType', 'title', 'creator', 'origin',
        'primarySource', 'directSourcePage', 'licenseId', 'licenseVersion',
        'licenseEvidence', 'commercialUseAllowed', 'modificationAllowed',
        'redistributionAllowed', 'attributionRequired', 'requiredAttributionText',
        'downloadDate', 'originalSha256', 'modifiedSha256', 'modificationsMade',
        'applicationLocations', 'reviewer', 'approvalState'
    )
    foreach ($field in $required) {
        if ($null -eq $record.PSObject.Properties[$field]) {
            $errors.Add("$($record.internalAssetId): missing field '$field'")
        }
    }

    if ($record.filename -match '(^|/)\.\.(/|$)' -or [System.IO.Path]::IsPathRooted($record.filename)) {
        $errors.Add("$($record.internalAssetId): filename must be a safe repository-relative path")
        continue
    }

    $fullPath = Join-Path $repo ($record.filename -replace '/', '\')
    if (Test-Path -LiteralPath $fullPath -PathType Leaf) {
        $actualHash = (Get-FileHash -LiteralPath $fullPath -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($record.modifiedSha256 -notmatch '^[a-f0-9]{64}$') {
            $errors.Add("$($record.internalAssetId): modifiedSha256 is not lowercase SHA-256")
        } elseif ($actualHash -ne $record.modifiedSha256) {
            $errors.Add("$($record.internalAssetId): checksum mismatch for $($record.filename)")
        }
    }

    if ($approvedLicenses -notcontains $record.licenseId) {
        $errors.Add("$($record.internalAssetId): unapproved license '$($record.licenseId)'")
    }
    if ($caseByCase -contains $record.licenseId -and $record.approvalState -ne 'approved') {
        $errors.Add("$($record.internalAssetId): case-by-case license is not approved")
    }
    if ($record.approvalState -ne 'approved') {
        $errors.Add("$($record.internalAssetId): approvalState must be 'approved' for shipped assets")
    }

    if ($record.origin -eq 'third-party') {
        foreach ($booleanField in @('commercialUseAllowed', 'modificationAllowed', 'redistributionAllowed')) {
            if ($record.$booleanField -ne $true) {
                $errors.Add("$($record.internalAssetId): $booleanField must be true")
            }
        }
        foreach ($urlField in @('primarySource', 'directSourcePage', 'licenseEvidence')) {
            if ($record.$urlField -notmatch '^https://') {
                $errors.Add("$($record.internalAssetId): $urlField must be an HTTPS primary-source URL")
            }
        }
        $ledgerMatches = @($ledgerRows | Where-Object internal_asset_id -eq $record.internalAssetId)
        if ($ledgerMatches.Count -ne 1) {
            $errors.Add("$($record.internalAssetId): expected exactly one CSV ledger row")
        }
        if ($record.attributionRequired -eq $true) {
            if ([string]::IsNullOrWhiteSpace($record.requiredAttributionText) -or
                -not $attributionText.Contains($record.requiredAttributionText)) {
                $errors.Add("$($record.internalAssetId): exact required attribution is missing")
            }
        }
    } elseif ($record.origin -eq 'first-party') {
        foreach ($field in @('generatorPath', 'generatorVersion', 'seedPolicy')) {
            if ($null -eq $record.PSObject.Properties[$field]) {
                $errors.Add("$($record.internalAssetId): first-party generated asset missing '$field'")
            }
        }
    } else {
        $errors.Add("$($record.internalAssetId): origin must be 'first-party' or 'third-party'")
    }
}

if ($errors.Count -gt 0) {
    $errors | ForEach-Object { Write-Error $_ }
    throw "verify-assets: FAILED with $($errors.Count) error(s)"
}

$thirdPartyCount = @($records | Where-Object origin -eq 'third-party').Count
$firstPartyCount = @($records | Where-Object origin -eq 'first-party').Count
Write-Output "verify-assets: PASS ($($discovered.Count) shipped visual files; $firstPartyCount first-party; $thirdPartyCount third-party)"
