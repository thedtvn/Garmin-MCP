import os
import pickle
import sys
import click
import uvicorn
import garth
from typing import Optional
from garmin_mcp import crate_mcp_server
from starlette.applications import Starlette


def eprint(*args, **kwargs):
    """
    Print function that can be used to print stderr messages in MCP server mode stdio.
    """
    print(*args, file=sys.stderr, **kwargs)

@click.command()
@click.option("--email", default=None,
              help="Garmin Connect email. If not provided, it will be read from the GARMIN_EMAIL environment variable.")
@click.option("--password", default=None,
              help="Garmin Connect password. If not provided, it will be read from the GARMIN_PASSWORD environment variable.")
@click.option("--port", default=3000, help="Port to run the MCP server SSE mode. Default is 3000.")
@click.option("--host", default="localhost", help="Host to run the MCP server SSE mode. Default is localhost.")
@click.option("--sse", is_flag=True, help="Run the MCP server in SSE and Streamable HTTP mode. Default is Stdio mode.")
def main(email: Optional[str], password: Optional[str], port: int, host: str, sse: bool):
    email = email or os.getenv("GARMIN_EMAIL")
    password = password or os.getenv("GARMIN_PASSWORD")
    if not email or not password:
        eprint("Email and password must be provided check --help")
        sys.exit(1)
    garmin_client = garth.Client()
    if os.path.exists("./auth/token.pikl"):
        with open("./auth/token.pikl", "rb") as f:
            garmin_client.oauth1_token, garmin_client.oauth2_token = pickle.load(f)
        token = garmin_client.refresh_oauth2()
        try:
            # noinspection PyStatementEffect
            garmin_client.user_profile
        except:
            os.remove("./auth/token.pikl")
            return main(email, password, port, host, sse)
        with open("./auth/token.pikl", "wb") as f:
            pickle.dump([garmin_client.oauth1_token, token], f)
        eprint("Token refreshed successfully. Using existing token from ./auth/token.pikl")
    else:
        token = garmin_client.login(email, password)
        if token[0] == "needs_mfa":
            eprint("MFA is required. Please turn on MFA in your Garmin account and run the script again.")
            sys.exit(1)
        if not os.path.exists("./auth"):
            os.makedirs("./auth")
        with open("./auth/token.pikl", "wb") as f:
            pickle.dump(token, f)
        eprint("Login successful. Token saved to ./auth/token.pikl")
    mcp_server = crate_mcp_server(port=port)
    if sse:
        streamable_http_app = mcp_server.streamable_http_app()
        sse_app = mcp_server.sse_app()
        async def lifespan(app):
            print("MCP server started in SSE mode.")
            print(f"You can access the SSE: http://{host}:{port}/sse")
            print(f"or streamable http: http://{host}:{port}/mcp")
            async with sse_app.router.lifespan_context(app), streamable_http_app.router.lifespan_context(app):
                yield
        starlette_app = Starlette(
            routes=streamable_http_app.routes + sse_app.routes,
            middleware=streamable_http_app.user_middleware + sse_app.user_middleware,
            lifespan=lifespan
        )
        config = uvicorn.Config(
            starlette_app,
            host=host,
            port=port,
            log_level=mcp_server.settings.log_level.lower(),
        )
        server = uvicorn.Server(config)
        server.run()
    else:
        eprint("Start Stdio server")
        mcp_server.run("stdio")


if __name__ == "__main__":
    main()
