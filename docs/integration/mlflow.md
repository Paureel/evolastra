# MLflow integration status

No MLflow dependency or adapter is shipped in this implementation. The core application and all integration tests remain independent of MLflow.

A future optional adapter may link Evolastra experiment, dataset, model, parameter, metric, and evaluation identities to an installed MLflow deployment. It must use documented MLflow APIs, redact before export, preserve canonical IDs, and avoid treating MLflow as the canonical semantic store. Until such an adapter is implemented and tested, this surface is intentionally deferred rather than represented by a mock.
