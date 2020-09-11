import nox

nox.options.sessions = "lint", "tests", "mypy"

locations = ["src/mplug/"]


@nox.session(python=["3.8", "3.7", "3.6", "3.5"])
def tests(session):
    args = session.posargs or ["--cov", *locations]
    session.run("poetry", "install", external=True)
    session.run("pytest", *args)


@nox.session(python="3.8")
def lint(session):
    args = session.posargs or locations
    session.run("poetry", "install", external=True)
    session.install("pylint")
    session.run("pylint", *args)


@nox.session(python="3.8")
def black(session):
    args = session.posargs or locations
    session.install("black")
    session.run("black", *args)


@nox.session(python=["3.8", "3.7"])
def mypy(session):
    args = session.posargs or locations
    session.install("mypy")
    session.run("mypy", *args)
