import os
from setuptools import setup, find_packages


if __name__ == '__main__':

	long_description = ''
	if os.path.exists('README.md'):
		with open('README.md', encoding='utf-8') as f:
			long_description = f.read()

	setup(
		name='conveyor',
		version='1.3.1',
		description='Library for creating cold-pipeline-oriented systems',
		long_description=long_description,
		long_description_content_type='text/markdown',
		author='mentalblood',
		install_requires=[
			'blake3',
			'peewee',
			'logama',
			'growing-tree-base'
		],
		packages=find_packages()
	)
