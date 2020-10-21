import csv
import datetime
from collections import OrderedDict
import sys

from peewee import *

db = SqliteDatabase('inventory.db')


class InputError(Exception):
    pass


class Product(Model):
    product_id = AutoField()
    product_name = CharField(unique=True)
    product_quantity = IntegerField()
    product_price = IntegerField()
    date_updated = DateTimeField()

    class Meta:
        database = db


def initialize():
    """Create database and table if they don't exist"""
    db.connect()
    db.create_tables([Product], safe=True)


def add_entry(dictionary):
    Product.create(
        product_name=dictionary['product_name'],
        product_quantity=int(dictionary['product_quantity']),
        product_price=dictionary['product_price'],
        date_updated=(dictionary['date_updated']))


def update_duplicate(dictionary, existing_product):
    existing_product.product_quantity = int(dictionary['product_quantity'])
    existing_product.product_price = dictionary['product_price']
    existing_product.date_updated = dictionary['date_updated']
    existing_product.save()


def add_csv():
    with open('inventory.csv', newline='') as csvfile:
        inventory_reader = csv.DictReader(csvfile, delimiter=",")
        rows = list(inventory_reader)
        for row in rows:
            row['date_updated'] = datetime.datetime.strptime(row['date_updated'], '%m/%d/%Y')
            row['product_price'] = round(float(row['product_price'].strip('$'))*100)
            try:
                add_entry(row)
            except IntegrityError:
                existing_product = Product.get(Product.product_name == row['product_name'])
                if row['date_updated'] >= existing_product.date_updated:
                    update_duplicate(row, existing_product)
                else:
                    pass


def print_heading(heading):
    print("")
    print(heading)
    print("-" * len(heading))


def print_product_details(selected_product):
    product = Product.get(Product.product_id == selected_product)
    print("ID:", product.product_id, " | ",
          "NAME:", product.product_name, " | ",
          "QUANTITY:", product.product_quantity, " | ",
          "PRICE: $%.2f" % float(product.product_price * .01), " | ",
          "Date Updated:", product.date_updated.strftime('%m/%d/%Y'))


def last_product_id():
    """Find final Product ID for View & Print Methods"""
    return Product.select().order_by(Product.product_id.desc()).get()


def menu_loop():
    """Show the menu"""
    choice = None
    heading = "INVENTORY DATABASE MENU"
    while choice not in menu:
        print_heading(heading)
        for key, value in menu.items():
            print('{}) {}'.format(key, value.__doc__))
        choice = input('\nMenu Action: ').lower().strip()
        if choice not in menu:
            print("\nInput Error. Please enter a valid letter per the list of menu options.")
    if choice in menu:
        menu[choice]()


def back_to_menu(question):
    stay = None
    while stay not in ['y', 'n']:
        stay = input(question).lower()
        if stay not in ['y', 'n']:
            print("\nInvalid Entry. Please try again with 'y' or 'n'.")
    return stay


def view_product_details():
    """View details of a specific product."""
    heading = "View Product Details"
    print_heading(heading)
    while True:
        try:
            selected_product = input("Enter Product ID to view details (1 - {}): ".format(last_product_id()))
            print_product_details(selected_product)
            if back_to_menu("\nWould you like to view more products (y/n): ") == 'n':
                break
        except DoesNotExist:
            print("\nThis Product ID does not exist. Please try again.")
        except ValueError:
            print("\nEntry must be a numeric. Please try again.")
    menu_loop()


def decimal_check(string):
    index = string.index(".")
    if len(string[index:]) > 3:
        return False
    else:
        return True


def add_new_product():
    """Add a new product to the database."""
    while True:
        heading = "Add A New Product"
        print_heading(heading)
        new_product_details = {'product_name': ""}
        while len(new_product_details['product_name']) == 0:
            new_product_details['product_name'] = input("Enter a product name: ")
            if len(new_product_details['product_name']) == 0:
                print("Product Name is a required field.")
        while True:
            try:
                new_product_details['product_price'] = input("Enter a product price ($#.##): ")
                if not decimal_check(new_product_details['product_price']):
                    raise InputError("Invalid entry. You may only enter up to two decimal places.")
                new_product_details['product_price'] = round(float(new_product_details['product_price'].strip('$'))*100)
                break
            except ValueError:
                print("Invalid Entry. Enter dollar amount in the format of '$#.##'")
            except InputError as err:
                print("{}".format(err))
        while True:
            try:
                new_product_details['product_quantity'] = int(input("Enter a product quantity: "))
                break
            except ValueError:
                print("Invalid Entry. Enter a numeric.")
        new_product_details['date_updated'] = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        try:
            add_entry(new_product_details)
            print("\nThis product has been added to the database.")
            print_product_details(last_product_id())
            if back_to_menu("\nWould you like to add another product (y/n): ") == 'n':
                break
        except IntegrityError:
            existing_product = Product.get(Product.product_name == new_product_details['product_name'])
            if new_product_details['date_updated'] >= existing_product.date_updated:
                print("\nA product with this name already exists:")
                print_product_details(existing_product.product_id)
                update = None
                while update not in ['y', 'n']:
                    update = input("Do you want to update this product with the details you entered? (y/n): ").lower()
                    if update == 'y':
                        update_duplicate(new_product_details, existing_product)
                        print("\nThis product has been updated in the database.")
                        print_product_details(existing_product.product_id)
                        break
                    if update == 'n':
                        print("This product was not updated in the database.")
                        break
                    else:
                        print("\nInvalid entry. Please try again")
            else:
                print("A product with the same name was added with a more recent Updated Date. "
                      "Therefore, your entry was not added.")
            if back_to_menu("Would you like to add another product (y/n): ") == 'n':
                break
    menu_loop()


def backup_database():
    """Make a backup of the entire contents of database."""
    heading = "Inventory Backup"
    print_heading(heading)
    with open('backup_inventory.csv', 'w') as csvfile:
        fieldnames = [
            'product_name',
            'product_price',
            'product_quantity',
            'date_updated'
            ]
        inventory_writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        inventory_writer.writeheader()
        for product in Product.select():
            inventory_writer.writerow({
                'product_name': product.product_name,
                'product_price': "$%.2f" % float(product.product_price * .01),
                'product_quantity': product.product_quantity,
                'date_updated': product.date_updated.strftime('%m/%d/%Y')
                })
    print("A backup inventory file has been created.")
    menu_loop()


def exit_program():
    """Exit the program."""
    done = None
    while done not in ['y', 'n']:
        done = input("Are you sure you want to exit the program? (y/n): ").lower()
        if done == 'y':
            sys.exit("Goodbye.")
        if done not in ['y', 'n']:
            print("Invalid entry. Please try again.")
        else:
            menu_loop()


menu = OrderedDict([
    ('v', view_product_details),
    ('a', add_new_product),
    ('b', backup_database),
    ('e', exit_program)
])


if __name__ == '__main__':
    initialize()
    add_csv()
    menu_loop()
