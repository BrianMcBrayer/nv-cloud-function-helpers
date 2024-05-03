import time
from concurrent import futures
import logging
import threading
import grpc
from grpc_health.v1 import health
from grpc_health.v1 import health_pb2
from grpc_health.v1 import health_pb2_grpc
from grpc_reflection.v1alpha import reflection
import echo_pb2
import echo_pb2_grpc


def _toggle_health(health_servicer: health.HealthServicer, service: str):
    next_status = health_pb2.HealthCheckResponse.SERVING
    while True:
        if next_status == health_pb2.HealthCheckResponse.SERVING:
            next_status = health_pb2.HealthCheckResponse.NOT_SERVING
        else:
            next_status = health_pb2.HealthCheckResponse.SERVING

        health_servicer.set(service, next_status)
        time.sleep(5)


def _configure_health_server(server: grpc.Server):
    health_servicer = health.HealthServicer(
            experimental_non_blocking=True,
            experimental_thread_pool=futures.ThreadPoolExecutor(max_workers=10),
    )
    health_pb2_grpc.add_HealthServicer_to_server(health_servicer, server)

    # Use a daemon thread to toggle health status
    toggle_health_status_thread = threading.Thread(
            target=_toggle_health,
            args=(health_servicer, "helloworld.Greeter"),
            daemon=True,
    )
    toggle_health_status_thread.start()


class Echo(echo_pb2_grpc.EchoServicer):
    def EchoMessage(self, request, context):
        time.sleep(0.001)
        return echo_pb2.EchoReply(message=f"{request.message}")

    def EchoMessageStreaming(self, request_iterator, context):
        for request in request_iterator:
            yield echo_pb2.EchoReply(message=f"{request.message}")


def serve():
    port = "8001"
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    echo_pb2_grpc.add_EchoServicer_to_server(Echo(), server)
    server.add_insecure_port("[::]:" + port)
    _configure_health_server(server)
    reflection.enable_server_reflection((
        echo_pb2.DESCRIPTOR.services_by_name['Echo'].full_name,
        reflection.SERVICE_NAME,
    ), server)
    server.start()
    print("Server started, listening on " + port)

    server.wait_for_termination()


if __name__ == "__main__":
    logging.basicConfig()
    serve()
