import nox


@nox.session(python=["3.8", "3.7", "3.6"])
def tests(session):
    args = session.posargs or ["--cov", "src/"]
    session.run("poetry", "install", external=True)
    session.run("pytest", *args)
