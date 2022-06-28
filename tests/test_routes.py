"""
Order API Service Test Suite

Test cases can be run with the following:
  nosetests -v --with-spec --spec-color
  coverage report -m
  codecov --token=$CODECOV_TOKEN

  While debugging just these tests it's convenient to use this:
    nosetests --stop tests/test_service.py:TestOrderService
"""

import os
import logging
import random
from unittest import TestCase
from unittest.mock import MagicMock, patch
from service import app
from service.models import db, Order, init_db, OrderStatus
from tests.factories import OrderFactory, ItemFactory
from service.utils import status  # HTTP Status Codes

BASE_URL = "/orders"

DATABASE_URI = os.getenv(
    "DATABASE_URI", "postgresql://postgres:postgres@localhost:5432/postgres"
)

######################################################################
#  T E S T   C A S E S
######################################################################
class Test(TestCase):
    """ REST API Server Tests """

    @classmethod
    def setUpClass(cls):
        """Run once before all tests"""
        app.config["TESTING"] = True
        app.config["DEBUG"] = False
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI
        app.logger.setLevel(logging.CRITICAL)
        init_db(app)

    @classmethod
    def tearDownClass(cls):
        """Runs once before test suite"""
        pass

    def setUp(self):
        """Runs before each test"""
        db.session.query(Order).delete()  # clean up the last tests
        db.session.commit()
        self.app = app.test_client()

    def tearDown(self):
        """Runs once after each test case"""
        db.session.remove()

    ######################################################################
    #  H E L P E R   M E T H O D S
    ######################################################################
    
    def _create_orders(self, count):
        """Factory method to create orders in bulk"""
        orders = []
        for _ in range(count):
            order = OrderFactory() 
            resp = self.app.post(BASE_URL, json=order.serialize())
            self.assertEqual(
                resp.status_code,
                status.HTTP_201_CREATED,
                "Could not create test Order",
            )
            new_order = resp.get_json()
            order.id = new_order["id"]
            orders.append(order)
        return orders

    ######################################################################
    #  P L A C E   T E S T   C A S E S   H E R E
    ######################################################################
    
    def test_index(self):
        """ It should call the home page """
        resp = self.app.get("/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn(b'Order REST API Service', resp.data)

    def test_create_order(self):
        """It should Create a new Order"""
        order = OrderFactory()
        resp = self.app.post(
            BASE_URL, json=order.serialize(), content_type="application/json"
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

        # Make sure location header is set
        location = resp.headers.get("Location", None)
        self.assertIsNotNone(location)

        # Check the data is correct
        new_order = resp.get_json()
        self.assertEqual(new_order["customer_id"], order.customer_id, "Customer id does not match")
        self.assertEqual(new_order["tracking_id"], order.tracking_id, "Tracking id does not match")
        self.assertEqual(new_order["status"], order.status.name, "Status does not match")
        self.assertEqual(len(new_order["order_items"]), len(order.order_items), "Items does not match")

        # Check that the location header was correct by getting it
        resp = self.app.get(location, content_type="application/json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        new_order = resp.get_json()
        self.assertEqual(new_order["customer_id"], order.customer_id, "Customer id does not match")
        self.assertEqual(new_order["tracking_id"], order.tracking_id, "Tracking id does not match")
        self.assertEqual(new_order["status"], order.status.name, "Status does not match")
        self.assertEqual(new_order["order_items"], order.order_items, "Items does not match")

    def test_update_order(self):
        """It should Update an existing Order"""
        # create an Order to update
        test_order = OrderFactory()
        resp = self.app.post(BASE_URL, json=test_order.serialize())
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

        # update the order
        new_order = resp.get_json()
        new_order_id = new_order["id"]
        new_order["customer_id"] = 9999
        new_order["tracking_id"] = 8888
        new_order["status"] = OrderStatus.CANCELLED.name
        
        resp = self.app.put(f"{BASE_URL}/{new_order_id}", json=new_order)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        updated_order = resp.get_json()
        self.assertEqual(updated_order["customer_id"], 9999)
        self.assertEqual(updated_order["tracking_id"], 8888)
        self.assertEqual(updated_order["status"], OrderStatus.CANCELLED.name)


    def test_create_orders_wrong_content_type(self):
        """ Create an order with wrong content type """
        order = OrderFactory()
        resp = self.app.post('/orders',
                             json=order.serialize(),
                             content_type='application/xml')

        self.assertEqual(resp.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    ######################################################################
    #  I T E M   T E S T   C A S E S
    ######################################################################

    def test_add_item(self):
        """It should Add an item to an order"""
        order = self._create_orders(1)[0]
        item = ItemFactory()
        resp = self.app.post(
            f"{BASE_URL}/{order.id}/items",
            json=item.serialize(),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        data = resp.get_json()
        logging.debug(data)
        self.assertEqual(data["order_id"], order.id)
        self.assertEqual(data["product_id"], item.product_id)
        self.assertEqual(data["quantity"], item.quantity)
        self.assertEqual(data["price"], item.price)

    def test_update_item(self):
        """It should Update an item on an order"""
        # create a known item
        order = self._create_orders(1)[0]
        item = ItemFactory()
        resp = self.app.post(
            f"{BASE_URL}/{order.id}/items",
            json=item.serialize(),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

        data = resp.get_json()
        logging.debug(data)
        item_id = data["id"]
        data["product_id"] = 9999
        data["quantity"] = 8888
        data["price"] = 7777

        # send the update back
        resp = self.app.put(
            f"{BASE_URL}/{order.id}/items/{item_id}",
            json=data,
            content_type="application/json",
        )
        print(resp)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        # retrieve it back
        resp = self.app.get(
            f"{BASE_URL}/{order.id}/items/{item_id}",
            content_type="application/json",
        )
        print("~~~~~~~~~~~~~~~~~~~~~~~~~", resp)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        data = resp.get_json()
        logging.debug(data)
        self.assertEqual(data["id"], item_id)
        self.assertEqual(data["order_id"], order.id)
        self.assertEqual(data["product_id"], 9999)
        self.assertEqual(data["quantity"], 8888)
        self.assertEqual(data["price"], 7777)