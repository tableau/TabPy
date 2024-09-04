# Running TabPy in Virtual Environment

<!-- toc -->

## Running TabPy in Python Virtual Environment

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
   1. Default TabPy

      ```sh
      tabpy
      ```

   2. Local TabPy

      To create a version of TabPy that incorporates locally-made changes,
      use pip to create a package from your local TabPy project and install
      it within that directory:

         ```sh
         pip install -e .
         ```

      Then start TabPy just like it was mentioned earlier

         ```sh
         tabpy
         ```

5. To deactivate virtual environment run:

   ```sh
   deactivate
   ```

## Running TabPy in an Anaconda Virtual Environment

To run TabPy in an Anaconda virtual environment follow the steps:
*NOTE: this assumes you have installed [Anaconda](https://www.anaconda.com/products/individual)
in a Windows environment*

1. For Windows open `Anaconda Prompt` from the Windows Start menu, for
Linux and Mac run shell.

2. Navigate to your home directory:
   1. On Windows run

      ```sh
      cd %USERPROFILE%
      ```

   2. For Linux and Mac run

      ```sh
      cd ~
      ```

3. Create the virtual Anaconda environment

    ```sh
    conda create --name my-tabpy-env python=3.12
    ```

4. Activate your virtual environment

   ```sh
   conda activate my-tabpy-env
   ```

5. Install TabPy to your new Anaconda environment by following the instructions
   on the [TabPy Server Install](server-install.md) documentation page.

6. Run TabPy:

   ```sh
   tabpy
   ```

7. To deactivate virtual environment run:

   ```sh
   conda deactivate
   ```
