from setuptools import setup, find_packages

setup(
    name="dicom_client",
    version="1.1.0",
    description="A command-line tool for managing DICOM files and servers.",
    author="Inès Benziane",
    author_email="i.benziane@institut-myologie.org",
    
    packages=find_packages(),
    
    py_modules=["cli", "cli_options"],
    
    install_requires=[
       'click>=8.0.0',
        'pynetdicom>=2.0.0',
        'pydicom>=2.3.0',
        'pandas>=1.5.0',      
        'openpyxl>=3.0.0',    
        'requests>=2.28.0',
    ],
    
    entry_points={
        'console_scripts': [
            'dicom-client=cli:cli',
        ],
    },

    python_requires='>=3.8',
)