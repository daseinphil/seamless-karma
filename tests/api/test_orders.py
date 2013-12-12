import json
import pytest
from seamless_karma.extensions import db
from seamless_karma.models import User
from factories import UserFactory, OrderFactory, OrganizationFactory, VendorFactory
import factory
from six.moves.urllib.parse import urlparse

def test_empty(client):
    response = client.get('/api/orders')
    assert response.status_code == 200
    obj = json.loads(response.data)
    assert obj['count'] == 0


def test_create_no_args(client):
    response = client.post('/api/orders')
    assert response.status_code == 400
    obj = json.loads(response.data)
    err = ("at least one pair of contributed_by and contributed_amount"
        " values is required")
    assert err == obj['message']


def test_create(client):
    org = OrganizationFactory.create()
    user = UserFactory.create(organization=org)
    vendor = VendorFactory.create()
    db.session.commit()
    response = client.post('/api/orders', data={
        "contributed_by": user.id,
        "contributed_amount": "8.50",
        "ordered_by_id": user.id,
        "vendor_id": vendor.id,
    })
    assert response.status_code == 201
    assert "Location" in response.headers
    obj = json.loads(response.data)
    assert "id" in obj
    url = response.headers["Location"]
    path = urlparse(url).path
    resp2 = client.get(path)
    assert resp2.status_code == 200
    created = json.loads(resp2.data)
    assert created["contributions"][0]["amount"] == "8.50"
