from setuptools import setup

package_name = 'scurid_proto'

setup(
    name=package_name,
    version='0.0.0',
    packages=['pb2'],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Ditlev Andersen',
    maintainer_email='ditlev.andersen@scurid.com',
    description='Shared protobuf Python package for Scurid ROS nodes.',
    license='None',
)