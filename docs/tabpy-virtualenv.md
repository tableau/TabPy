# Running TabPy in Python Virtual Environment

<!-- toc -->

To run TabPy in Python virtual environment follow steps
below.

## Windows Specific Steps

1. Install `virtualenv` package:

   ```sh
   pip install virtualenv
   ```

2. Create virtual environment:

   ```sh
   virtualenv <name>
   ```

3. Activate the environment:

   ```sh
   <name>\Scripts\activate
   ```

4. Run TabPy:

   ```sh
   startup.cmd
   ```

5. To deactivate virtual environment run:

   ```sh
   deactivate
   ```

## Linux and Mac Specific Steps

1. Install `virtualenv` package:

   ```sh
   pip install virtualenv
   ```

2. Create virtual environment:

   ```sh
   virtualenv <name>
   ```

3. Activate the environment:

   ```sh
   <name>/bin/activate
   ```

4. Run TabPy:

   ```sh
   ./startup.sh
   ```

5. To deactivate virtual environment run:

   ```sh
   deactivate
   ```
