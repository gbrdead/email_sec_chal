import setuptools

setuptools.setup(
    name = "email-sec-cache",
    description = "Email Security Cache",
    version = "0.1.0",
    license="GPLv3+",
    
    author = "Vladimir Panov",
    author_email = "gbr@voidland.org",
    maintainer = "Vladimir Panov",
    maintainer_email = "gbr@voidland.org",
    
    packages=[
        "email_sec_cache",
        "gpgmime",
        "test.email_sec_cache"],
                 
    install_requires=[
        "python-gnupg >= 0.3.8",
        "beautifulsoup4 >= 4.4.0"],
                 
    test_suite = "test.email_sec_cache")
