# coding=utf-8
from __future__ import unicode_literals

from seamless_karma.extensions import db
from seamless_karma.sql_types import Currency
import sqlalchemy as sa
from sqlalchemy.orm import backref
from sqlalchemy.sql import type_coerce
from sqlalchemy.ext.hybrid import hybrid_property, hybrid_method
from decimal import Decimal


class Organization(db.Model):
    __tablename__ = 'organizations'
    id = db.Column(db.Integer, primary_key=True)
    seamless_id = db.Column(db.Integer, unique=True)
    name = db.Column(db.String(256), unique=True, nullable=False)
    default_allocation = db.Column(Currency(scale=2))

    def __repr__(self):
        return u"<Organization {!r}>".format(self.name)


class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    seamless_id = db.Column(db.Integer, unique=True)
    username = db.Column(db.String(256), unique=True, nullable=False)
    first_name = db.Column(db.String(256), nullable=False)
    last_name = db.Column(db.String(256), nullable=False)
    allocation = db.Column(Currency(scale=2), nullable=False)

    organization_id = db.Column(
        db.Integer, db.ForeignKey('organizations.id'), nullable=False
    )
    organization = db.relationship(
        Organization, backref=db.backref('users', lazy="dynamic")
    )

    @classmethod
    def create(cls, username, first_name, last_name, organization, allocation=None, seamless_id=None):
        return cls(
            username=username,
            first_name=first_name,
            last_name=last_name,
            organization=organization,
            seamless_id=seamless_id,
            allocation=allocation or organization.default_allocation
        )

    def __repr__(self):
        return u'<User "{first} {last}">'.format(
            first=self.first_name, last=self.last_name)

    @hybrid_property
    def contributed_orders(self):
        """
        All orders that this user contributed to, but did not place.
        """
        return (o for o in self.orders if o.ordered_by_id != self.id)

    @contributed_orders.expression
    def contributed_orders(cls):
        return (Order.join(OrderContribution)
            .filter(OrderContribution.user_id == cls.id)
            .filter(Order.user_id != cls.id)
        )

    @hybrid_property
    def karma(self):
        """
        Total amount this user has contributed to other peoples' orders,
        minus total amount others have contributed to this user's orders.
        """
        total = (sum(oc.amount for oc in self.order_contributions if oc.is_external)
               - sum(o.external_contribution for o in self.own_orders))
        return total or Decimal('0.00')

    @karma.expression
    def karma(cls):
        given = (db.session.query(
            sa.func.coalesce(
                sa.func.sum(OrderContribution.amount), Decimal('0.00')
            ).label('given'))
            .join(Order)
            .filter(OrderContribution.user_id == cls.id)
            .filter(Order.ordered_by_id != cls.id)
        )
        received = (db.session.query(
            sa.func.coalesce(
                sa.func.sum(OrderContribution.amount), Decimal('0.00')
            ).label('received'))
            .join(Order)
            .filter(OrderContribution.user_id != cls.id)
            .filter(Order.ordered_by_id == cls.id)
        )
        return type_coerce(
            (given.as_scalar() - received.as_scalar()).label('karma'),
            Currency
        )

    @hybrid_method
    def participated_on(self, date):
        return any(o for o in self.orders if o.for_date == date)

    @participated_on.expression
    def participated_on(cls, date):
        return (
            db.session.query(Order)
            .join(OrderContribution)
            .filter(OrderContribution.user_id == cls.id)
            .filter(Order.for_date == date)
            .exists()
        )

    @hybrid_method
    def unallocated(self, date):
        allocated = sum(o.user_contribution(self.id) for o in self.orders
            if o.for_date == date) or Decimal('0.00')
        return self.allocation - allocated

    @unallocated.expression
    def unallocated(cls, date):
        allocated = (db.session.query(
            sa.func.coalesce(
                sa.func.sum(OrderContribution.amount),
                Decimal('0.00')
            ).label('allocated'))
            .join(Order)
            .filter(Order.for_date == date)
            .filter(OrderContribution.user_id == cls.id)
        )
        return type_coerce(
            (cls.allocation - allocated).label('unallocated'),
            Currency
        )


class Vendor(db.Model):
    __tablename__ = 'vendors'
    id = db.Column(db.Integer, primary_key=True)
    seamless_id = db.Column(db.Integer, unique=True)
    name = db.Column(db.String(256), nullable=False)
    latitude = db.Column(db.Numeric)
    longitude = db.Column(db.Numeric)


class Order(db.Model):
    __tablename__ = 'orders'
    id = db.Column(db.Integer, primary_key=True)
    seamless_id = db.Column(db.Integer, unique=True)
    for_date = db.Column(db.Date, nullable=False)
    placed_at = db.Column(db.DateTime, nullable=False)

    vendor_id = db.Column(
        db.Integer, db.ForeignKey('vendors.id'), nullable=False
    )
    vendor = db.relationship(Vendor, backref="orders")
    ordered_by_id = db.Column(
        db.Integer, db.ForeignKey('users.id'), nullable=False
    )
    ordered_by = db.relationship(User, backref="own_orders")
    contributors = db.relationship(
        User, secondary="order_contributions", backref="orders"
    )

    def __repr__(self):
        return u"<Order {date}>".format(date=self.for_date.isoformat())

    @classmethod
    def create(
        cls, for_date, placed_at, ordered_by_id, contributions,
        seamless_id=None, vendor_id=None
    ):
        order = cls(
            seamless_id=seamless_id,
            for_date=for_date,
            placed_at=placed_at,
            ordered_by_id=ordered_by_id,
            vendor_id=vendor_id,
        )
        for contributor_id, amount in contributions.items():
            OrderContribution(
                user_id=contributor_id,
                amount=amount,
                order=order,
            )
        return order

    @hybrid_property
    def total_amount(self):
        return sum(oc.amount for oc in self.contributions)

    @total_amount.expression
    def total_amount(cls):
        return (db.session.query(sa.func.sum(OrderContribution.amount))
            .filter(OrderContribution.order_id == cls.id)
            .label('total_amount'))

    @hybrid_property
    def personal_contribution(self):
        return sum(oc.amount for oc in self.contributions
            if oc.user_id == self.ordered_by_id)

    @personal_contribution.expression
    def personal_contribution(cls):
        return (db.session.query(sa.func.sum(OrderContribution.amount))
            .filter(OrderContribution.order_id == cls.id)
            .filter(OrderContribution.user_id == cls.ordered_by_id)
            .label('personal_contribution'))

    @hybrid_property
    def external_contribution(self):
        return sum(oc.amount for oc in self.contributions
            if oc.user_id != self.ordered_by_id)

    @external_contribution.expression
    def external_contribution(cls):
        return (db.session.query(sa.func.sum(OrderContribution.amount))
            .filter(OrderContribution.order_id == cls.id)
            .filter(OrderContribution.user_id != cls.ordered_by_id)
            .label('external_contribution'))

    @hybrid_method
    def user_contribution(self, user_id):
        total = sum(oc.amount for oc in self.contributions
            if oc.user_id == user_id)
        return total or Decimal('0.00')

    @user_contribution.expression
    def user_contribution(cls, user_id):
        return (db.session.query(
            sa.func.coalesce(
                sa.func.sum(OrderContribution.amount),
                Decimal('0.00')
            ))
            .filter(OrderContribution.order_id == cls.id)
            .filter(OrderContribution.user_id == user_id)
            .label('user_{}_contribution'.format(user_id))
        )


class OrderContribution(db.Model):
    __tablename__ = 'order_contributions'
    user_id = db.Column(
        db.Integer, db.ForeignKey('users.id'), primary_key=True
    )
    order_id = db.Column(
        db.Integer, db.ForeignKey('orders.id'), primary_key=True
    )

    user = db.relationship(User, backref="order_contributions")
    order = db.relationship(
        Order, backref=backref(
            "contributions",
            cascade='all, delete-orphan', single_parent=True
        )
    )
    amount = db.Column(Currency(scale=2), nullable=False)

    def __repr__(self):
        return u"<OrderContribution {}>".format(self.amount)

    @hybrid_property
    def beneficiary(self):
        return self.order.ordered_by

    @beneficiary.expression
    def beneficiary(cls):
        return User.query.join(Order).filter(Order.id == cls.order_id)

    @hybrid_property
    def is_external(self):
        return self.user_id != self.order.ordered_by_id

    @is_external.expression
    def is_external(cls):
        return (
            (cls.order_id == Order.id) and
            (cls.user_id == Order.ordered_by_id)
        )
