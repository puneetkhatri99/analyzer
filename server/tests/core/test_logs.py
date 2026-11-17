from app.core.config import Settings
from app.core.logs import writes_files


def test_log_files_are_skipped_only_in_production_with_axiom() -> None:
    def files(**kw: str | None) -> bool:
        return writes_files(Settings(_env_file=None, **kw))

    assert files()  # local, no Axiom
    assert files(axiom_token="t")  # local with Axiom: files kept as the fallback
    assert files(app_env="production")  # production without Axiom: files are the only log
    assert not files(app_env="production", axiom_token="t")
