from django.test import TestCase
from jdhapi.models.author import Author


class TestAuthorCreation(TestCase):
    def setUp(self):
        self.authorComplete = Author.objects.create(
            id="1",
            email="johndoe@example.com",
            lastname="Doe",
            firstname="John",
            orcid="0000-0000-0000-0000",
            affiliation="University",
            city="City",
            country="US",
        )
        self.authorUncomplete = Author.objects.create(
            id="2",
            lastname="Doe",
            firstname="Alice",
            affiliation="University",
        )

    def test_access_author_api(self):
        response = self.client.get("/api/authors/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 2)

        author_complete = response.data["results"][0]
        author_uncomplete = response.data["results"][1]

        self.assertEqual(author_complete["firstname"], "John")
        self.assertEqual(author_uncomplete["firstname"], "Alice")

        self.assertEqual(author_complete["country"], "US")
        self.assertEqual(author_uncomplete["country"], "")
