import unittest
import threading
import _thread
import pyarrow
import os
import pyarrow.csv as csv

from tabpy.tabpy_server.app.arrow_server import FlightServer
import tabpy.tabpy_server.app.arrow_server as pa

class TestArrowServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        host = "localhost"
        port = 13620
        scheme = "grpc+tcp"
        location = "{}://{}:{}".format(scheme, host, port)
        cls.arrow_server = FlightServer(host, location)
        def start_server():
            pa.start(cls.arrow_server)
        _thread.start_new_thread(start_server, ())
        cls.arrow_client = pyarrow.flight.FlightClient(location)
    
    @classmethod
    def tearDownClass(cls):
        cls.arrow_server.shutdown()

    def setUp(self):
        self.resources_path = os.path.join(os.path.dirname(__file__), "resources")
        self.arrow_server.flights = {}

    def test_server_do_put(self):
        data_path = os.path.join(self.resources_path, "data.csv")
        table = csv.read_csv(data_path)
        descriptor = pyarrow.flight.FlightDescriptor.for_path(data_path)
        writer, _ = self.arrow_client.do_put(descriptor, table.schema)
        writer.write_table(table)
        writer.close()
        flight_info = list(self.arrow_server.list_flights(None, None))
        self.assertEqual(len(flight_info), 1)

    def test_server_do_get(self):
        data_path = os.path.join(self.resources_path, "data.csv")
        table = csv.read_csv(data_path)
        descriptor = pyarrow.flight.FlightDescriptor.for_path(data_path)
        writer, _ = self.arrow_client.do_put(descriptor, table.schema)
        writer.write_table(table)
        writer.close()
        self.assertEqual(len(self.arrow_server.flights), 1)
        info = self.arrow_client.get_flight_info(descriptor)
        endpoint = info.endpoints[0]
        reader = self.arrow_client.do_get(endpoint.ticket)
        self.assertTrue(reader.read_all().equals(table))
        self.assertEqual(len(self.arrow_server.flights), 0)

    def test_list_flights_on_new_server(self):
        flight_info = list(self.arrow_server.list_flights(None, None))
        self.assertEqual(len(flight_info), 0)
