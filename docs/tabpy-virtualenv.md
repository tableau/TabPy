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
      my-tabpy-env/bin/activate
      ```

4. Run TabPy:

   ```sh
   tabpy
   ```

5. To deactivate virtual environment run:

   ```sh
   deactivate
   ```
