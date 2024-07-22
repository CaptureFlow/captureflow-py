import requests
import random

BASE_URL = "http://localhost:9999"

def create_user(email, password):
    response = requests.post(f"{BASE_URL}/api/login/", json={"email": email, "password": password})
    print("RESPONSE = ", response.text)
    return response.json()

def create_car(name, year, brand):
    response = requests.post(f"{BASE_URL}/api/v1/cars/", json={"name": name, "year": year, "brand": brand})
    return response.json()

def create_stock(car_id, quantity):
    response = requests.post(f"{BASE_URL}/api/v1/stocks/", json={"car_id": car_id, "quantity": quantity})
    return response.json()

def create_seller(name, cpf, phone):
    response = requests.post(f"{BASE_URL}/api/v1/sellers/", json={"name": name, "cpf": cpf, "phone": phone})
    return response.json()

def create_buyer(name, phone, address):
    response = requests.post(f"{BASE_URL}/api/v1/buyers/", json={"name": name, "phone": phone, "address": address})
    return response.json()

def create_sale(car_id, seller_id, buyer_id):
    response = requests.post(f"{BASE_URL}/api/v1/sales/", json={"car_id": car_id, "seller_id": seller_id, "buyer_id": buyer_id})
    return response.json()

def main():
    # Create users
    users = [
        create_user(f"user{i}@example.com", f"password{i}") for i in range(1, 6)
    ]
    print("Created users:", users)

    # Create cars
    cars = [
        create_car("Sedan", 2022, "Toyota"),
        create_car("SUV", 2023, "Honda"),
        create_car("Hatchback", 2021, "Ford"),
        create_car("Truck", 2022, "Chevrolet"),
        create_car("Coupe", 2023, "BMW")
    ]
    print("Created cars:", cars)

    # Create stock for cars
    stocks = [create_stock(car['id'], random.randint(1, 10)) for car in cars]
    print("Created stocks:", stocks)

    # Create sellers
    sellers = [
        create_seller(f"Seller {i}", f"CPF{i}", f"555-0000{i}") for i in range(1, 4)
    ]
    print("Created sellers:", sellers)

    # Create buyers with addresses
    addresses = [
        {
            "cep": f"1234{i}",
            "public_place": f"Street {i}",
            "city": "New York",
            "district": f"District {i}",
            "state": "NY"
        } for i in range(1, 6)
    ]
    buyers = [
        create_buyer(f"Buyer {i}", f"555-1111{i}", address) for i, address in enumerate(addresses, 1)
    ]
    print("Created buyers:", buyers)

    # Create sales
    sales = []
    for _ in range(10):
        car = random.choice(cars)
        seller = random.choice(sellers)
        buyer = random.choice(buyers)
        sale = create_sale(car['id'], seller['id'], buyer['id'])
        sales.append(sale)
    print("Created sales:", sales)

    # Read some data to verify
    response = requests.get(f"{BASE_URL}/api/v1/cars/")
    print("All cars:", response.json())

    response = requests.get(f"{BASE_URL}/api/v1/sales/")
    print("All sales:", response.json())

if __name__ == "__main__":
    main()