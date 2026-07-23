"""Movie pipeline exceptions with stable error codes."""


class MoviePipelineError(Exception):
    code = "movie_pipeline_error"


class InvalidMovieRequest(MoviePipelineError):
    code = "invalid_movie_request"


class MovieValidationError(MoviePipelineError):
    code = "movie_validation_error"


class RenderBackendUnavailable(MoviePipelineError):
    code = "render_backend_unavailable"
