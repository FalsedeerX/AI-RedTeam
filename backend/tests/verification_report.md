(venv) (base) paulcavounis@Pauls-MacBook-Pro-4 backend % python -m pytest tests/ -v 
=============================================== test session starts ================================================
platform darwin -- Python 3.11.5, pytest-9.0.3, pluggy-1.6.0 -- /Users/paulcavounis/Downloads/app_ideas/senior_design/AI-RedTeam/venv/bin/python
cachedir: .pytest_cache
rootdir: /Users/paulcavounis/Downloads/app_ideas/senior_design/AI-RedTeam/backend
plugins: langsmith-0.6.9, anyio-4.13.0
collected 22 items                                                                                                 

tests/test_clerk_auth.py::test_extract_bearer_token_accepts_standard_header PASSED                           [  4%]
tests/test_clerk_auth.py::test_extract_bearer_token_case_insensitive PASSED                                  [  9%]
tests/test_clerk_auth.py::test_extract_bearer_token_rejects_missing_scheme PASSED                            [ 13%]
tests/test_clerk_auth.py::test_extract_bearer_token_rejects_empty PASSED                                     [ 18%]
tests/test_clerk_auth.py::test_verify_clerk_jwt_accepts_valid_token PASSED                                   [ 22%]
tests/test_clerk_auth.py::test_verify_clerk_jwt_rejects_expired_token PASSED                                 [ 27%]
tests/test_clerk_auth.py::test_verify_clerk_jwt_rejects_wrong_issuer PASSED                                  [ 31%]
tests/test_clerk_auth.py::test_verify_clerk_jwt_rejects_when_audience_required_but_missing PASSED            [ 36%]
tests/test_clerk_auth.py::test_verify_clerk_jwt_accepts_matching_audience PASSED                             [ 40%]
tests/test_clerk_auth.py::test_verify_clerk_jwt_raises_when_clerk_disabled PASSED                            [ 45%]
tests/test_clerk_auth.py::test_verify_clerk_jwt_rejects_empty_token PASSED                                   [ 50%]
tests/test_clerk_auth.py::test_verify_clerk_jwt_rejects_garbage_token PASSED                                 [ 54%]
tests/test_deps.py::test_clerk_path_upserts_and_returns_local_uuid PASSED                                    [ 59%]
tests/test_deps.py::test_clerk_path_falls_back_placeholder_email_when_claim_missing PASSED                   [ 63%]
tests/test_deps.py::test_clerk_path_returns_401_when_header_missing PASSED                                   [ 68%]
tests/test_deps.py::test_clerk_path_returns_401_on_verification_failure PASSED                               [ 72%]
tests/test_deps.py::test_clerk_path_rejects_token_without_subject PASSED                                     [ 77%]
tests/test_deps.py::test_dev_bypass_accepts_valid_uuid PASSED                                                [ 81%]
tests/test_deps.py::test_dev_bypass_rejects_missing_header PASSED                                            [ 86%]
tests/test_deps.py::test_dev_bypass_rejects_malformed_uuid PASSED                                            [ 90%]
tests/test_deps.py::test_dev_bypass_ignored_when_clerk_enabled PASSED                                        [ 95%]
tests/test_deps.py::test_auth_disabled_returns_503 PASSED                                                    [100%]

================================================= warnings summary =================================================
app/core/config.py:9
  /Users/paulcavounis/Downloads/app_ideas/senior_design/AI-RedTeam/backend/app/core/config.py:9: PydanticDeprecatedSince20: Support for class-based `config` is deprecated, use ConfigDict instead. Deprecated in Pydantic V2.0 to be removed in V3.0. See Pydantic V2 Migration Guide at https://errors.pydantic.dev/2.12/migration/
    class Settings(BaseSettings):

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
========================================== 22 passed, 1 warning in 1.33s ===========================================
(venv) (base) paulcavounis@Pauls-MacBook-Pro-4 backend % 