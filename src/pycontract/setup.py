from setuptools import setup

package_name = 'pycontract'

setup(
    name=package_name,
    version='0.1.0',
    packages=['pycontract'],
    data_files=[
        # Install the marker file (for ROS)
         
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=[
        'setuptools', 
        'pandas'
    ],
    zip_safe=True,
    maintainer='Klaus Havelund',
    maintainer_email='havelund@gmail.com',
    description='Runtime verification and contract monitoring',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
        ],
    },
)
