import json
from langchain import hub

# Pull the template
template = hub.pull("souzatharsis/podcastfy_multimodal")

# Custom JSON encoder to handle non-serializable objects
class CustomEncoder(json.JSONEncoder):
    def default(self, obj):
        # If the object is not serializable, convert it to a string representation
        if hasattr(obj, '__dict__'):
            return obj.__dict__
        return str(obj)

# Format and save the template in markdown format
def save_readable_template_markdown(template, file_name="template_output.md"):
    # Open the file in write mode
    with open(file_name, 'w') as file:
        # Write markdown header
        file.write("# Template Structure and Data\n\n")
        
        # Check if template is in dictionary (JSON) format
        if isinstance(template, dict):
            # Pretty print the dictionary as a JSON string with indentation and save it in markdown code block
            file.write("```json\n")
            file.write(json.dumps(template, indent=4, cls=CustomEncoder))
            file.write("\n```\n")
        else:
            # If not JSON, iterate through the attributes and write them in key-value format inside markdown code blocks
            file.write("## Template Data\n\n")
            for key, value in template.__dict__.items():
                file.write(f"### {key}:\n")
                # Check if the value is complex (like a list or dictionary) and format accordingly
                if isinstance(value, (list, dict)):
                    file.write("```json\n")
                    file.write(json.dumps(value, indent=4, cls=CustomEncoder))
                    file.write("\n```\n")
                else:
                    # For simple text values
                    file.write(f"```\n{value}\n```\n")

# Save the formatted template details to a markdown file
save_readable_template_markdown(template)

print(f"Template saved successfully to 'template_output.md'")
