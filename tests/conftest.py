"""pytest configuration and shared fixtures."""

import textwrap

import pytest


@pytest.fixture
def generic_naming_code():
    """Python code with lots of generic AI-style names."""
    return textwrap.dedent("""
        def process_data(data, result, temp):
            output = data
            response = result
            item = temp
            obj = {}
            val = None
            info = []
            stuff = "test"
            return output

        def handle_request(data):
            result = data
            return result
    """)


@pytest.fixture
def over_commented_code():
    """Python code with excessive obvious comments."""
    return textwrap.dedent("""
        # increment counter
        counter += 1
        # return the result
        return result
        # loop through items
        for item in items:
            # append item to list
            result.append(item)
        # initialize the value
        value = 0
        # set the flag
        flag = True
        # open the file
        with open('file.txt') as f:
            # read the file
            content = f.read()
    """)


@pytest.fixture
def placeholder_code():
    """Python code with TODOs and empty bodies."""
    return textwrap.dedent("""
        def process():
            # TODO: implement this
            pass

        def handle():
            # FIXME: broken
            pass

        def empty_func():
            pass

        # HACK: temporary workaround
        x = 1
        # TODO: remove this later
        y = 2
    """)


@pytest.fixture
def security_issues_code():
    """Python code with multiple security anti-patterns."""
    return textwrap.dedent("""
        import subprocess

        password = "super_secret_password123"
        api_key = "sk-abcdefghijklmnop"

        def run_command(user_input):
            subprocess.call(user_input, shell=True)
            eval(user_input)

        def query_db(name):
            cursor.execute("SELECT * FROM users WHERE name = " + name)
    """)


@pytest.fixture
def repetitive_code():
    """Python code with copy-paste functions."""
    return textwrap.dedent("""
        def process_user(user):
            result = []
            for item in user:
                result.append(item)
            return result

        def process_order(order):
            result = []
            for item in order:
                result.append(item)
            return result

        def process_product(product):
            result = []
            for item in product:
                result.append(item)
            return result
    """)


@pytest.fixture
def clean_code():
    """Python code with good naming and no AI smell."""
    return textwrap.dedent("""
        \"\"\"Module for processing customer orders.\"\"\"

        from decimal import Decimal
        from typing import List


        class OrderProcessor:
            \"\"\"Handles order validation and fulfillment.\"\"\"

            def __init__(self, tax_rate: Decimal) -> None:
                self.tax_rate = tax_rate

            def calculate_total(self, line_items: List[dict]) -> Decimal:
                \"\"\"Compute the order total including tax.\"\"\"
                subtotal = sum(
                    Decimal(str(item["price"])) * item["quantity"]
                    for item in line_items
                )
                return subtotal * (1 + self.tax_rate)

            def validate_order(self, order: dict) -> bool:
                \"\"\"Return True if the order passes all validation checks.\"\"\"
                if not order.get("customer_id"):
                    return False
                if not order.get("line_items"):
                    return False
                return all(
                    item.get("product_id") and item.get("quantity", 0) > 0
                    for item in order["line_items"]
                )
    """)


@pytest.fixture
def high_ratio_code():
    """Python code with more docstrings than actual logic."""
    return textwrap.dedent("""
        \"\"\"
        This module provides a comprehensive set of utility functions
        for processing and handling various types of data inputs and outputs.
        It includes helpers for string manipulation, number formatting,
        and general-purpose data transformations.
        \"\"\"

        def convert(value):
            \"\"\"
            This function handles the conversion of the input value.
            It takes the value as a parameter and returns the converted result.
            The function processes the input by applying the necessary transformations.
            Returns the final converted output after all processing is complete.
            \"\"\"
            return str(value)

        def get_data(source):
            \"\"\"
            This function retrieves data from the given source.
            It accepts a source parameter and fetches the corresponding data.
            The function manages the retrieval process and returns the data.
            Returns the data retrieved from the source as a result.
            \"\"\"
            return source
    """)
