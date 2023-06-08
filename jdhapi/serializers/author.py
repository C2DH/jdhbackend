from jdhapi.serializers.abstract import AbstractSerializer
from rest_framework import serializers
from ..models.author import Author


class AuthorSerializer(serializers.ModelSerializer):
    abstracts = AbstractSerializer(many=True, read_only=True)

    class Meta:
        model = Author
        fields = ['id', 'lastname', 'firstname', 'affiliation', 'email', 'orcid', 'abstracts', 'main_author']


class AuthorSlimSerializer(serializers.ModelSerializer):

    class Meta:
        model = Author
        fields = ['id', 'lastname', 'firstname', 'affiliation', 'orcid', 'main_author']
