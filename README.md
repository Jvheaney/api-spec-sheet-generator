# API Spec Sheet Generator
Generator to create an md file of REST API endpoints and the required parameters for Spring Boot projects automatically. This file uses only glob and re, two libraries in standard Python.

## Use Cases
I wrote this to make working with other people easier. Instead of having to manually create a list of endpoints I created and hand them off to frontend developers, I could just run this script and hand them the markdown output.

#### Why not use Swagger?
I really just wanted something lightweight that didn't add libraries to my codebase. I also enjoy challenging my regex knowledge, so it was a win-win.

## How to Use
### Placement of Script
Place this file in some root directory, and modify/add to `CONTROLLERS_PARENT_PATHS` and `MODELS_PARENT_PATHS`, following the structure of `{root}/to/spring/boot/project/controllers` and `{root}/to/spring/boot/project/models`.

### Blacklist attributes in models
You can blacklist certain model attributes from appearing on the output spec sheet as a parameter. These are useful for sequence generated model attributes like `uniqueId`, `isActive`, and `nextBillingDate`. You can set these by adding to the array `MODEL_PARAMETERS_BLACKLIST`.

### Execution and Output
Run the script by using `python EndpointSpecSheetGenerator.py` and it will output a file titled `api_endpoints.md`.

## Caveats
While it is about as general as I can imagine to make it, there are certainly areas that are likely unique to how I code which would interfere with this being a "plug-and-play" solution for everyone. You can adjust everything from within the single file.

