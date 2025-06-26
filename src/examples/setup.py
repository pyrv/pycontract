from setuptools import setup

package_name = 'pycontract_examples'

setup(
    name=package_name,
    version='0.1.0',
    packages=[],  # no importable Python packages; only standalone scripts
    py_modules=[],
    data_files=[
        # Install the marker file (for ROS)
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml', 'run_monitor.py']),
    ],
    install_requires=['setuptools', 'pycontract'],
    zip_safe=True,
    maintainer='Klaus Havelund',
    maintainer_email='havelund@gmail.com',
    description='Examples for pycontract',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            # no console scripts; users can run run_monitor.py directly
        ],
    },
)
