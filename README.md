# Seamless Karma [![Build Status](https://travis-ci.org/singingwolfboy/seamless-karma.svg?branch=master)](https://travis-ci.org/singingwolfboy/seamless-karma) [![Coverage Status](https://coveralls.io/repos/singingwolfboy/seamless-karma/badge.png)](https://coveralls.io/r/singingwolfboy/seamless-karma)


Seamless.com is a website that allows you to order food for delivery or takeout.
In addition to individual orders, they also have a corporate program where a
business allow its employees to order lunch through Seamless, and allocate
a certain amount of money per employee per day to pay for that lunch. Employees
may share their allocation with other employees in the company: for example, if
each employee gets a $10 allocation per day, Alice can order $8 of food and
give her remaining $2 to Bob, who can then order $12 of food. Or, Alice and
Bob can pool their money, and together buy $20 of food.

This project is a tool to help employees efficiently manage their Seamless
allocations. Your Seamless "Karma" is simply the total amount of money that
other employees have used from your daily allocation, minus the total amount of
money that you have used from other employees' daily allocations.

## Security

This project has no security whatsoever: there are no user accounts, no passwords,
and anyone can change any piece of data in the system at any time. It's
essentially an API layer over a SQL database. It is assumed that organizing
and tracking your Seamless Karma is not a security-critical component of your
infrastructure, and an authentication and permissions framework would provide
needless complexity in using the application.

In layman's terms: anyone can modify their Seamless Karma at any time (or anyone
else's Seamless Karma). This game only works if everyone plays by the rules.
Please be nice!

## API Documentation

The Seamless Karma API is documented using [Sphinx](http://sphinx-doc.org/). You
can [view the rendered documentation on Read The
Docs](http://seamless-karma.readthedocs.org).

## Deploying

This project can be deployed to Heroku using the [multi
buildpack](https://github.com/ddollar/heroku-buildpack-multi):

```bash
$ heroku config:set BUILDPACK_URL=git://github.com/ddollar/heroku-buildpack-multi.git
```

If you want to speed up the deployment, and you don't care about the web
front-end, you can just use the [Python
buildpack](https://github.com/heroku/heroku-buildpack-python):

```bash
$ heroku config:set BUILDPACK_URL=git://github.com/heroku/heroku-buildpack-python.git
```
