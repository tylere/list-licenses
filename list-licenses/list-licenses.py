#!/usr/bin/env python

import commands
import re
import json
import dircache
import os
import tarfile
import urllib
import urllib2
import yaml

class CondaInstallation:
  '''Object representing a conda installation on a machine.'''
  
  def conda_info(self):
    # Example: conda info --json
    cmd = 'conda info --json'
    return json.loads(commands.getoutput(cmd))
    
  def package_dir(self):
    return self.conda_info()['pkgs_dirs'][0]
  
  def get_conda_environments(self):
    '''Get a list of conda environments that are available.'''
    # Example: conda info -e
    cmd = 'conda info -e'
    lines = commands.getoutput(cmd).split('\n')
    # Remove the non-path items.
    lines = [line for line in lines if line.startswith('/')]
    return lines


class CondaEnv:
  '''Object representing a conda environment.
  
  Reference: http://conda.pydata.org/docs/using/envs.html
  '''
  name = None

  def __init__(self, conda_install, env):
    self.conda_install = conda_install
    self.name = env

  def get_conda_packages(self):
    # Example: conda list --explicit -n python2
    cmd = 'conda list --explicit -n {env}'.format(env=self.name)

    lines = commands.getoutput(cmd).split('\n')

    # Remove comments
    packages = [line for line in lines if not (line.startswith('#') or line.startswith('@'))]

    return packages


class CondaPackage:
  '''Object representing a conda package.
  
  Reference: http://conda.pydata.org/docs/using/pkgs.html
  '''
  
  url = None
  license_file_obj = None
  license_file_source = None
  
  _url_pattern = '(https?)://(.+?)/(.+/.+)/(.+)-(.+)-(.+).tar.bz2'


  def __init__(self, conda_install, package_url):
    self.conda_install = conda_install
    self.url = package_url
    
    # Examples:
    #'https://conda.anaconda.org/conda-forge/linux-64/backports.shutil_get_terminal_size-1.0.0-py35_0.tar.bz2'
    # ('https', 'conda.anaconda.org', 'conda-forge/linux-64', 'backports.shutil_get_terminal_size', '1.0.0', 'py35_0')
    # https://conda.anaconda.org/conda-forge/linux-64/blas-1.1-openblas.tar.bz2'
    # ('https', 'conda.anaconda.org', 'conda-forge/linux-64', 'blas', '1.1', 'openblas')
    
    pattern = re.compile(self._url_pattern)
    match = pattern.match(self.url)
    groups = match.groups()
    self.package_protocol = groups[0]
    self.package_domain = groups[1]
    self.package_base_path = groups[2]
    self.package_name = groups[3]
    self.package_version = groups[4]
    self.package_type = groups[5]
  
  def get_package_license_info(self):
    
    # Define where to find the meta.yaml file stored on GitHub for different conda repository configurations.
    META_URL = {
      'repo.continuum.io': 'https://raw.githubusercontent.com/ContinuumIO/anaconda-recipes/master/{0}/meta.yaml',
      'conda.anaconda.org': 'https://raw.githubusercontent.com/conda-forge/{0}-feedstock/master/recipe/meta.yaml'
    }

    pkg_path = '{pkg_dir}/{name}-{version}-{pkg_type}/info'.format(
        pkg_dir=self.conda_install.package_dir(),
        name=self.package_name,
        version=self.package_version,
        pkg_type=self.package_type
    )
    
    print('')
    print('Processing: {0}'.format(self.package_name))
    
    try:
      pkg_info_list = dircache.listdir(pkg_path)
    except OSError as e:
      print('{0}The expected package path was not found.'.format(' ' * 2))
      print('{0}{1}'.format(' ' * 2, e))
      
      # Stop if we haven't manually investigated this file
      #
      # cycler:
      #  does not install anything in /opt/conda/pkgs/cycler-0.10.0-py35_0
      #  installs an egg in lib/python3.5/site-packages/cycler-0.10.0-py3.5.egg
      if self.package_name not in ['cycler']
      import ipdb; ipdb.set_trace()
      return

    print('{0}pkg_info_list: {1}'.format(' ' * 2, pkg_info_list))
    
    # Find any file in the archive that contains the phrase "LICENSE"
    license_files = [s for s in pkg_info_list if "LICENSE" in s]
    
    if any(license_files):
      print('{0}Found the following LICENSE files!'.format(' ' * 6))
      self.license_file_source = 'Found in package: {0}'.format(pkg_path)
      
      # For DEBUGGING
      for license_file in license_files:
        print('{0}license_filename: {1}'.format(' ' * 8, pkg_path + license_file))
      
      self.license_file_obj = [open(os.path.join(pkg_path,f)) for f in license_files]
    else:
      print('{0}DID NOT FIND A LOCAL LICENSE FILE!'.format(' '* 2))
    
      # Determine the package provider
      print('{0}Package Domain: {1}'.format(' ' * 4, self.package_domain))
    
      if self.package_domain in ['repo.continuum.io', 'conda.anaconda.org']:
        meta_url = META_URL[self.package_domain].format(self.package_name)
        print('{0}meta_url: {1}'.format(' ' * 4, meta_url))
        #filename, headers = urllib.urlretrieve(meta_url)
        file_meta = yaml.load(urllib2.urlopen(meta_url))
      
        # Extract information on the repo source.
        #import ipdb; ipdb.set_trace()
        #
        source_fn = file_meta['source']['fn']
        if source_fn.endswith('.tar.gz'):
          source_base = source_fn[:-7]
        else:
          print('{0}Expected URL to end in .tar.gz found {1}!'.format(source_fn[-7:]))
          raise
        source_url = file_meta['source']['url']
        print('{0}source_url: {1}'.format(' ' * 4, source_url))
      
        # Download the tar.bz file.
        filename, headers = urllib.urlretrieve(source_url)
        with tarfile.open(name=filename) as mytar:
          tarfile_names = mytar.getnames()
          
          # Find any file in the archive that contains the phrase "LICENSE"
          license_files = [s for s in tarfile_names if "LICENSE" in s]
          
          if any(license_files):
            print('{0}Found the following LICENSE files!'.format(' ' * 6))
            self.license_file_source = 'Extracted from {0}'.format(source_url)
            
            for license_file in license_files:
              print('{0}license_filename: {1}'.format(' ' * 8, license_file))
            self.license_file_obj = [mytar.extractfile(f) for f in license_files]
          
            #import ipdb; ipdb.set_trace()
            #pass
          
          else:
            print('{0}Searching the remote TAR file: Did not find a LICENSE file!'.format(' ' * 6))
            import ipdb; ipdb.set_trace()
            pass
      
      else:
        print('{0}No domain match for {1}'.format(' ' * 4, self.package_domain()))

    return self


def main():
  
  conda_env_list = CondaInstallation().get_conda_environments()
  #print('conda_env_list:', conda_env_list)
  
  conda_install = CondaInstallation()
  #conda_info = conda_install.conda_info()
  #pkgs_dir = conda_info['pkgs_dirs'][0]
  
  pkg_url_list = CondaEnv(conda_install, env='root').get_conda_packages()
  pkg_info = [CondaPackage(conda_install, pkg_url).get_package_license_info() for pkg_url in pkg_url_list[6:7]]

  #import ipdb; ipdb.set_trace()
  package_count = 0
  for pkg in pkg_info:
    if pkg is not None:
      package_count += 1
      print('')
      print('{0}PACKAGE #{1} - {2}'.format(' ' * 0, package_count, pkg.package_name))
      print('{0}{1}'.format(' ' * 2, pkg.license_file_source))
      print('{0}{1}'.format(' ' * 2, 'License files:'))
      for f in pkg.license_file_obj:
        print('{0}{1}'.format(' ' * 4, f.name))

if __name__ == "__main__":
    main()