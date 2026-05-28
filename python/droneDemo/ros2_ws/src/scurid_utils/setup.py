from setuptools import setup

package_name = 'scurid_utils'

setup(
    name=package_name,
    version='0.0.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools', 'pyyaml'],
    zip_safe=True,
    maintainer='Ditlev Andersen',
    maintainer_email='ditlev.andersen@scurid.com',
    description='Shared utility functions for Scurid ROS2 nodes',
    license='There is none',
)