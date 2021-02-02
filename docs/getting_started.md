# Mopeka-Pro-Check - Getting Started

## Install

``` bash
pip install --upgrade mopeka_pro_check
```

## Usage

look at `example/test_service.py` for the two supported methods

### Notes

* This has only been tested on Linux, PI, Hassio. The `bleson` package (used for BLE) says it is cross platform but it has not been validated.
* In my usage I had to use `sudo` to be able to access the bluetooth adapter. I am sure you could configure this better. 
    ```bash
    sudo python3 example/test_service.py
    ```
