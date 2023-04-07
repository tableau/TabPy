import unittest
import threading
import pyarrow
import os
import pyarrow.csv as csv

from tabpy.tabpy_server.app.arrow_server import FlightServer
import tabpy.tabpy_server.app.arrow_server as pa

class TestArrowServer(unittest.TestCase):
    def setUp(self):
        self.resources_path = os.path.join(os.path.dirname(__file__), "resources")
        # Set up a flight server and start it
        host = "localhost"
        port = 13620
        scheme = "grpc+tcp"
        location = "{}://{}:{}".format(scheme, host, port)
        self.arrow_server = FlightServer(host, location)
        def start_server():
            pa.start(self.arrow_server)
        t = threading.Thread(target=start_server, args=(), daemon=True)
        t.start()

        # Set up a flight client
        self.arrow_client = pyarrow.flight.FlightClient(location)

    def tearDown(self):
        self.arrow_server.shutdown()
        self.arrow_server = None
        self.arrow_client = None

    def test_list_flights_on_new_server(self):
        flight_info = list(self.arrow_server.list_flights(None, None))
        self.assertEqual(len(flight_info), 0)

    def test_server_do_put(self):
        data_path = os.path.join(self.resources_path, "data.csv")
        table = csv.read_csv(data_path)
        descriptor = pyarrow.flight.FlightDescriptor.for_path(data_path)
        writer, _ = self.arrow_client.do_put(descriptor, table.schema)
        writer.write_table(table)
        writer.close()
        flight_info = list(self.arrow_server.list_flights(None, None))
        self.assertEqual(len(flight_info), 1)