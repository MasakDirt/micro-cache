from typing import Self

from pydantic import AliasChoices, Field, HttpUrl, model_validator
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict


class CliSettings(BaseSettings):
    """Send a payload to micro-cache and record every response as one JSON line.

    The body is sent exactly as given so that server-side rejections can be
    tested too. -H is the host flag because argparse reserves -h for help.
    """

    model_config = SettingsConfigDict(
        cli_parse_args=True,
        cli_prog_name="cache-cli",
        cli_exit_on_error=False,
        case_sensitive=True,
    )

    host: HttpUrl = Field(
        HttpUrl("http://localhost:8000"),
        validation_alias=AliasChoices("H", "host"),
        description="server base URL",
    )
    repeat: int = Field(
        1, ge=1, validation_alias=AliasChoices("r", "repeat"), description="number of iterations"
    )
    input: str | None = Field(
        None,
        validation_alias=AliasChoices("i", "input"),
        description="input file with the JSON body, '-' for stdin",
    )
    json_: str | None = Field(
        None, validation_alias=AliasChoices("j", "json"), description="the JSON body itself"
    )
    output: str = Field(
        "-", validation_alias=AliasChoices("o", "output"), description="output file, '-' for stdout"
    )

    @model_validator(mode="after")
    def one_body_source(self) -> Self:
        if self.input is not None and self.json_ is not None:
            raise ValueError("--input and --json cannot be combined")
        return self

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        # Command line only: an unrelated HOST variable must not redirect the tool.
        return (init_settings,)
