# ML Integration Boundary

The application does not currently run verified ML inference. `backend/app/services/interfaces/` contains application-level service contracts, but they are not connected to inference. The API now reports ML analysis as unavailable instead of returning fabricated diagnoses.

The repository also contains files under the root `ml/` directory, including model artifacts and metadata. Their compatibility, preprocessing, output semantics, runtime dependencies, and integration with the application are **NOT VERIFIED** by this application audit. No weights or artifacts were changed.

Do not report model accuracy, disease classifications, severity, Grad-CAM, video tracking, or plant aggregation as current application functionality. Integrate those only after inspecting real ML source/config/artifacts and validating end-to-end behavior.
