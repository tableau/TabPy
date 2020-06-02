# Running TabPy in Python Virtual Environment

<!-- toc -->

To run TabPy in Python virtual environment follow the steps:

1. Install `virtualenv` package:

   ```sh
   pip install virtualenv
   ```

2. Create virtual environment (replace `my-tabpy-env` with
   your virtual environment name):

   ```sh
   virtualenv my-tabpy-env
   ```

3. Activate the environment.
   1. For Windows run

      ```sh
      my-tabpy-env\Scripts\activate
      ```

   2. For Linux and Mac run

      ```sh
      source my-tabpy-env/bin/activate
      ```

4. Run TabPy:

   ```sh
   tabpy
   ```

5. To deactivate virtual environment run:

   ```sh
   deactivate
   ```

# Running TabPy in an Anaconda Virtual Environment

To run TabPy in an Anaconda virtual environment follow the steps:
*NOTE: this assumes you have installed [Anaconda](https://www.anaconda.com/products/individual) in a Windows environment*

1. Open `Anaconda Prompt` from the Windows Start menu

2. Navigate to your home directory:
*TabPy will need to be able to the `tabpy_log.log` file on startup*

   ```cd %USERPROFILE%   ```

3. Create the virtual Anaconda environment
*Inserting the TabPy version number into the name of your Conda environment is optional, but may help you distinguish your environments, should you have multiple available to you.*

    ```conda create --name TabPy<version-here> python=3.7      ```

4. Activate your virtual environment

	```conda activate TabPy<version-here>```

5. Install TabPy to your new Anaconda environment by following the instructions on the [TabPy Server Install](https://github.com/tableau/TabPy/blob/master/docs/server-install.md) documentation page.

7. Run TabPy:

   ```sh
   tabpy
   ```

8. To deactivate virtual environment run:

   ```conda deactivate   ```
