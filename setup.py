import setuptools

setuptools.setup(
    name = "email-sec-chal",
    description = "Email Security CTF Challenge",
    version = "1.0.0",
    license="GPLv3+",
    
    author = "Vladimir Panov",
    author_email = "gbr@voidland.org",
    maintainer = "Vladimir Panov",
    maintainer_email = "gbr@voidland.org",
    
    packages=[
        "email_sec_chal",
        "test.email_sec_chal"],
                 
    install_requires=[
        "python-gnupg >= 0.3.8",
        "beautifulsoup4 >= 4.4.1",
        "html2text >= 2016.1.8",
        "requests >= 2.9.1"],
                 
    test_suite = "test.email_sec_chal")
