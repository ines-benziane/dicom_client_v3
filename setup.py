from setuptools import setup, find_packages

setup(
    name="dicom_client",
    version="1.0.0",
    description="A command-line tool for managing DICOM files and servers.",
    author="Inès Benziane",
    author_email="i.benziane@institut-myologie.org",
    
    packages=find_packages(),
    
    py_modules=["cli"],
    
    install_requires=[
        'click',
        'pynetdicom',
    ],
    
    entry_points={
        'console_scripts': [
            'dicom-client=cli:cli',
        ],
    },
)