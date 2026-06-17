from __future__ import annotations

from pathlib import Path

import typer

from kws_testset.config import load_config

app = typer.Typer(help="KWS testset platform CLI")


@app.command()
def doctor(config: Path = typer.Option(Path("configs/app.yaml"), help="Config path")) -> None:
    cfg = load_config(config)
    cfg.app.data_dir.mkdir(parents=True, exist_ok=True)
    (cfg.app.data_dir / "library" / "sources").mkdir(parents=True, exist_ok=True)
    (cfg.app.data_dir / "library" / "variants").mkdir(parents=True, exist_ok=True)
    (cfg.app.data_dir / "exports").mkdir(parents=True, exist_ok=True)
    typer.echo(f"config={cfg.config_path}")
    typer.echo(f"data_dir={cfg.app.data_dir}")
    typer.echo(f"target_keyword={cfg.app.target_keyword}")
    typer.echo("doctor=ok")


@app.command()
def serve(
    config: Path = typer.Option(Path("configs/app.yaml"), help="Config path"),
    host: str = typer.Option("127.0.0.1", help="Host"),
    port: int = typer.Option(8000, help="Port"),
) -> None:
    import uvicorn

    from kws_testset.app import create_app

    fastapi_app = create_app(config_path=config)
    uvicorn.run(fastapi_app, host=host, port=port)
