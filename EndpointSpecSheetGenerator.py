import glob
import re

CONTROLLERS_PARENT_PATHS=["./controllers/"]
MODELS_PARENT_PATHS=["./models/","./DTOs/"]

#Some common parameters in models that don't need to be included in the spec
#Some exmaples of this can be "uniqueId", "isActive"
#Get applied globally
MODEL_PARAMETERS_BLACKLIST = []

models = {} #Dict of models, this gets built up as controllers are parsed
endpoints = [] #Array of endpoints, the elements will be dicts
model_paths = {} #Dict of model name and model path for quick locating
controller_file = []
controllers = []
#Go into controllers
for path in CONTROLLERS_PARENT_PATHS:
    controllers.extend(glob.glob(path + "**/*.java", recursive=True))

#Find paths of all the models and cache the locations based on name
#We will only parse the model file if it's required by an endpoint
for path in MODELS_PARENT_PATHS:
    files = glob.glob(path + "**/*.java", recursive=True)
    for file in files:
        data = re.search(r"\/([A-Za-z]+).java", file)
        model_paths[data.group(1)] = file


def fetch_model(model_name):
    model = models.get(model_name)

    if model is None:
        #We need to scan it
        model = scan_model(model_name)
        if model is None:
            return None
    return model


def scan_model(model_name):
    model = {}
    model_path = model_paths.get(model_name)
    if model_path is None:
        return None
    model_requirements = {}
    with open(model_path) as file:
        previous_line = ""
        for line in file:
            data = re.findall(r"(?:private|public)\s*([A-Za-z]+)\s*([A-Za-z]+);", line)
            for (data_type, variable_name) in data:
                if variable_name not in MODEL_PARAMETERS_BLACKLIST and previous_line != "@Transient" and "@Transient" not in line:
                    model_requirements['data_type'] = data_type
                    model_requirements['param_type'] = "Body"
                    model_requirements['required'] = "false" #This is later determined by the endpoint
                    model[variable_name] = model_requirements.copy()
            previous_line = re.sub(r"\s+", "", line, flags=re.UNICODE)
    models[model_name] = model.copy()
    return model

index = 0
endpoint = {}
endpoint['endpoint'] = ""
endpoint['method'] = ""
endpoint['requirements'] = {}
model_varaible_names = []
variable_to_model = {}
set_required = {}
removed_param = {}
for controller in controllers:
    with open(controller) as file:
        for line in file:
            if "@RequestMapping" in line:
                #We are starting a new method, therefore push the data, and restart data
                if len(endpoint['endpoint']) != 0:
                    controller_file.append(index)
                    endpoints.append(endpoint.copy())
                    endpoint['endpoint'] = ""
                    endpoint['method'] = ""
                    endpoint['requirements'] = {}
                    model_varaible_names = []
                    variable_to_model = {}
                    set_required = {}
                    removed_param = {}

                #We will capture the endpoint and method
                data = re.search(r"@RequestMapping\(\s*value\s*\=\s*\"([A-Za-z\/\{\}]+)\"\,\s*method\s*=\s*RequestMethod.([A-Z]+)\)", line)
                endpoint['endpoint'] = data.group(1)
                endpoint['method'] = data.group(2)
            if "@RequestParam" in line:
                #This is a parameter we need to capture
                data = re.findall(r"@RequestParam(?:\((?:\s*value\s*\=\s*){0,1}\"([A-Za-z0-9]+)\"(?:\s*\,\s*required\s*\=\s*(true|false)){0,1}\s*\)){0,1}\s*([A-Za-z]+)\s*([A-Za-z0-9]+)", line)
                for (form_name, required, data_type, variable_name) in data:
                    if len(required) == 0:
                        #Spring Boot defaults this to true
                        required = "true"
                    if len(form_name) == 0:
                        form_name = variable_name
                    requirement_data = {}
                    requirement_data['data_type'] = data_type
                    requirement_data['required'] = required
                    if endpoint['method'] == "GET":
                        requirement_data['param_type'] = "Query"
                    else:
                        requirement_data['param_type'] = "Body"

                    endpoint['requirements'][form_name] = requirement_data
            if "@PathVariable" in line:
                #This is a parameter we need to capture
                data = re.findall(r"@PathVariable(?:\(\"(?:[A-Za-z0-9]+)+\"\)|\(\s*value\s*=\s*\"([A-Za-z0-9]+)\"\,\s*required\s*\=\s*(true|false)\)){0,1}\s*([A-Za-z]+)\s*([A-Za-z]+)", line)

                #May or may not have ("name") after @PathVariable. If not, we use the name of the Java variable.
                for (path_variable_name, required, data_type, variable_name) in data:
                    if len(required) == 0:
                        required = "true"
                    requirement_data = {}
                    requirement_data['data_type'] = data_type
                    requirement_data['required'] = required
                    requirement_data['param_type'] = "Path"

                    if len(path_variable_name) == 0:
                        #No variable name, so we use the name of the Java variable.
                        endpoint['requirements'][variable_name] = requirement_data
                    else:
                        endpoint['requirements'][path_variable_name] = requirement_data
            if "@ModelAttribute" in line:
                #This is a parameter we need to capture
                data = re.findall(r"@ModelAttribute\s*([A-Za-z]+)\s*([A-Za-z]+)", line)

                #We capture the model name (used to get the requirements from it's model file) and the variable name
                #Variable name we are going to use in future line iterations to identify required parameters
                #We will be doing this by checking is {variable_name}.get{balh}() exists in an if.
                #Not the most intelligent way to check if these params are required, but good enough assuming the controller's dev checked

                #If parameter is checked or used, it's required
                #If parameter is not checked or used, we assume it's optional

                for (model_name, variable_name) in data:

                    #Has model been parsed
                    model = fetch_model(model_name)
                    if model is not None:
                        #We add this model variable name as an item of interest
                        model_varaible_names.append(variable_name)
                        #We add reference to the model via variable name
                        variable_to_model[variable_name] = model_name
                        #We add the requirements of the model to the endpoint requirements
                        endpoint['requirements'].update(model)
            if re.search(r"([A-Za-z]+).get([A-Za-z]+)\(\)", line):
                data = re.findall(r"([A-Za-z]+).get([A-Za-z]+)\(\)", line)
                for (variable_name, data_name) in data:
                    if set_required.get(data_name) is None and variable_name in model_varaible_names:
                        #Set first letter to lowercase since convention is that it's getFirtstname when the variable is firstname
                        data_name_corrected = data_name[0].lower() + data_name[1:]
                        #Find in endpoint requirements and set required to true
                        requirement = endpoint['requirements'].get(data_name_corrected)
                        if requirement is not None:
                            requirement.update({"required": "true"})
                            set_required[data_name] =  True
            if re.search(r"([A-Za-z]+).set([A-Za-z]+)\(", line):
                data = re.findall(r"([A-Za-z]+).set([A-Za-z]+)\(", line)
                for (variable_name, data_name) in data:
                    if removed_param.get(data_name) is None and variable_name in model_varaible_names:
                        #Set first letter to lowercase since convention is that it's getFirtstname when the variable is firstname
                        data_name_corrected = data_name[0].lower() + data_name[1:]
                        #Find in endpoint requirements and remove from params (since it is being set after the fact)
                        #We do this unless it has been explicitly set to required = true
                        if endpoint['requirements'].get(data_name_corrected) is not None and endpoint['requirements'].get(data_name_corrected).get("required") != "true":
                            endpoint['requirements'].pop(data_name_corrected)

        #Flush the endpoint if it exists, this is crucial on the first and last file
        if len(endpoint['endpoint']) != 0:
            controller_file.append(index)
            endpoints.append(endpoint.copy())
            endpoint['endpoint'] = ""
            endpoint['method'] = ""
            endpoint['requirements'] = {}
            model_varaible_names = []
            variable_to_model = {}
            set_required = {}
            removed_param = {}

        index = index + 1

##Print to file

previous_controller = ""
endpoint_index = 0
f = open("api_endpoints.md", "w")
f.write("# API Endpoints:")
for i in controller_file:

    #Header apply
    if previous_controller != controllers[i]:
        previous_controller = controllers[i]
        data = re.search(r"\/([A-Za-z]+).java", previous_controller)
        f.write(f"\n\n## {data.group(1)}\n")

    f.write(f"### {endpoints[endpoint_index]['endpoint']} - {endpoints[endpoint_index]['method']}\n")
    f.write(f"#### Requirements:\n")
    for requirement in list(endpoints[endpoint_index]['requirements'].keys()):
        f.write(f"<br />Name: ``{requirement}``\n<br />")
        f.write(f"Required: ``{endpoints[endpoint_index]['requirements'].get(requirement).get('required')}``\n<br />")
        f.write(f"Param type: ``{endpoints[endpoint_index]['requirements'].get(requirement).get('param_type')}``\n<br />")
        f.write(f"Data type: ``{endpoints[endpoint_index]['requirements'].get(requirement).get('data_type')}``\n<br />")
    f.write("\n\n")
    endpoint_index = endpoint_index + 1
f.close()
