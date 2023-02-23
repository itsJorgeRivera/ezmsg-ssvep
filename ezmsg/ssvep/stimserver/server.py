import asyncio
import http.server
import ssl
import logging
import json

from pathlib import Path
from dataclasses import field, dataclass

import ezmsg.core as ez
from ezmsg.sigproc.sampler import SampleTriggerMessage

import websockets
import websockets.server
import websockets.exceptions

import panel

from typing import AsyncGenerator, Optional

logger = logging.getLogger( __name__ )

@dataclass(frozen = True)
class StimServerSettingsMessage:
    cert: Optional[Path] = None
    key: Optional[Path] = None
    ca_cert: Optional[Path] = None
    host: str = '0.0.0.0'
    port: int = 8080
    ws_port: int = 5545

class StimServerSettings(ez.Settings, StimServerSettingsMessage):
    ...

class StimServerState( ez.State ):
    trigger_queue: "asyncio.Queue[SampleTriggerMessage]" = field( 
        default_factory = asyncio.Queue 
    )
    event_queue: "asyncio.Queue[SampleTriggerMessage]" = field(
        default_factory = asyncio.Queue
    )

class StimServer(ez.Unit):

    SETTINGS: StimServerSettings
    STATE: StimServerState

    OUTPUT_SAMPLETRIGGER = ez.OutputStream(SampleTriggerMessage)
    OUTPUT_EVENT = ez.OutputStream(SampleTriggerMessage)

    @ez.publisher(OUTPUT_SAMPLETRIGGER) 
    async def publish_trigger(self) -> AsyncGenerator:
        while True:
            output = await self.STATE.trigger_queue.get()
            yield self.OUTPUT_SAMPLETRIGGER, output

    @ez.publisher(OUTPUT_EVENT)
    async def publish_event(self) -> AsyncGenerator:
        while True:
            output = await self.STATE.event_queue.get()
            yield self.OUTPUT_EVENT, output

    @ez.task
    async def start_websocket_server(self) -> None:

        async def connection(websocket: websockets.server.WebSocketServerProtocol, path):
            logger.info('Client Connected to Websocket Input')

            try:
                while True:
                    data = json.loads(await websocket.recv())
                    if isinstance(data, dict):

                        msg_type = data.get('type', None)

                        if msg_type == 'LOG':
                            ...

                        elif msg_type == 'LOGJSON':
                            ...

                        elif msg_type == 'EVENT':
                            self.STATE.event_queue.put_nowait(
                                SampleTriggerMessage(
                                    value = data.get('value', None)
                                )
                            )

                        elif msg_type == 'TRIGGER':

                            period = None
                            start = data.get('start', None)
                            stop = data.get('stop', None)
                            if start is not None and stop is not None:
                                period = (start, stop)
                                
                            self.STATE.trigger_queue.put_nowait(
                                SampleTriggerMessage(
                                    value = data.get('value', None),
                                    period = period
                                )
                            )

                        else:
                            logger.warn(f'Unknown message type from websocket client: {msg_type=}')

                    else:
                        logger.warn('Unknown message from websocket client')

            except websockets.exceptions.ConnectionClosedOK:
                logger.info('Websocket Client Closed Connection')
            except asyncio.CancelledError:
                logger.info('Websocket Client Handler Task Cancelled!')
            except Exception as e:
                logger.warn('Error in websocket server:', e)
            finally:
                logger.info('Websocket Client Handler Task Concluded')

        try:
            ssl_context = None
            if self.SETTINGS.cert:
                ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER) 

                if self.SETTINGS.ca_cert:
                    ssl_context.load_verify_locations(self.SETTINGS.ca_cert)

                ssl_context.load_cert_chain( 
                    certfile = self.SETTINGS.cert, 
                    keyfile = self.SETTINGS.key 
                )

            server = await websockets.server.serve(
                connection,
                self.SETTINGS.host,
                self.SETTINGS.ws_port,
                ssl = ssl_context
            )

            await server.wait_closed()

        finally:
            logger.info( 'Closing Websocket Server' )

    def panel(self) -> panel.viewable.Viewable:
        return panel.Column(
            f"""
            <script language="JavaScript">
                document.write('<h1><a href="' + window.location.protocol + '//' + window.location.hostname + ':{self.SETTINGS.port}' + '" >Go to Stim Server running on port {self.SETTINGS.port}</a></h1>' );
            </script>
            """,
        )

    @ez.main
    def serve(self):

        directory = str((Path(__file__).parent / 'web'))

        class Handler(http.server.SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory = directory, **kwargs)

        address = ( self.SETTINGS.host, self.SETTINGS.port )
        httpd = http.server.HTTPServer( address, Handler )

        if self.SETTINGS.cert:
            httpd.socket = ssl.wrap_socket(
                httpd.socket,
                server_side = True,
                certfile = self.SETTINGS.cert,
                keyfile = self.SETTINGS.key,
                ca_certs = str(self.SETTINGS.ca_cert) if self.SETTINGS.ca_cert is not None else None,
                ssl_version = ssl.PROTOCOL_TLS_SERVER
            )

        httpd.serve_forever()
        

### DEV/TEST APPARATUS

from ezmsg.testing.debuglog import DebugLog

class StimServerTestSystem(ez.Collection):

    SETTINGS: StimServerSettings

    TASK_SERVER = StimServer()
    DEBUG = DebugLog()

    def configure(self) -> None:
        return self.TASK_SERVER.apply_settings(self.SETTINGS)

    def network(self) -> ez.NetworkDefinition:
        return (
            (self.TASK_SERVER.OUTPUT_SAMPLETRIGGER, self.DEBUG.INPUT),
        )

if __name__ == '__main__':

    import argparse

    parser = argparse.ArgumentParser(
        description = 'Training Server Test Script'
    )

    parser.add_argument(
        '--cert',
        type = lambda x: Path( x ),
        help = "Certificate file for frontend server",
        default = None
    )

    parser.add_argument(
        '--key',
        type = lambda x: Path( x ),
        help = "Private key for frontend server [Optional -- assumed to be included in --cert file if omitted)",
        default = None
    )

    parser.add_argument(
        '--cacert',
        type = lambda x: Path( x ),
        help = "Certificate for custom authority [Optional]",
        default = None
    )

    class Args:
        cert: Optional[Path]
        key: Optional[Path]
        cacert: Optional[Path]

    args = parser.parse_args(namespace = Args)

    settings = StimServerSettings(
        cert = args.cert,
        key = args.key,
        ca_cert = args.cacert
    )

    system = StimServerTestSystem( settings )
    ez.run_system( system )



