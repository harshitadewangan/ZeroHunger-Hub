
import pymongo
from bson import ObjectId
import os

uri = "mongodb+srv://honeydewangan86_db_user:VMeAQMluSa9hIWdy@cluster0.p3yhn2g.mongodb.net/?appName=Cluster0"
client = pymongo.MongoClient(uri)
db = client.zerohungerhub

print("--- Reviews ---")
for r in db.reviews.find().limit(5):
    print(r)

print("\n--- Food Posts ---")
for f in db.food_posts.find().limit(2):
    print(f)

print("\n--- Bookings ---")
for b in db.bookings.find().limit(2):
    print(b)
