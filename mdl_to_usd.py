import os
import sys
import re

MAP_NAMES = {
	'Diffuse': {'name': 'BaseColor', 'id': 'ND_image_color3', 'type': 'color3f', 'port': 'base_color'}, 
	'reflection_glossiness': {'name': 'Roughness', 'id': 'ND_image_float', 'type': 'float', 'port': 'specular_roughness'},
	'reflection_metalness': {'name': 'Metallic', 'id': 'ND_image_float', 'type': 'float', 'port': 'metalness'},
	'normal_map': {'name': 'Normal', 'id': 'ND_image_vector3', 'type': 'vector3f', 'port': 'normal'}
}

MATERIAL = {}

def read_file(path):
	with open(path, 'r') as file:
		for line in file:
			yield line.strip()


def get_properties():
	global MDL
	global line
	output = {}
	while re.match(r'^\)(?:\.\w+)?[,;]$', line) is None:
		name, value = line.rstrip(',').split(' : ')
		if value == '::templates::vray_maps::VRayBitmap(':
			line = next(MDL)
			value = get_properties()
		elif value.startswith('texture_2d'):
			match = re.match(r'texture_2d\("(.*)".*', value)
			value = match.group(1)
		elif value == '::templates::vray_maps::VRayNormalMap_bump(':
			line = next(MDL)
			continue
		else:
			# prep values
			value = value.rstrip('f')
			value = value.lstrip('color')

		output[name] = value

		line = next(MDL)
	
	return output


def usd_shader(name, properties):

	output = f'''
	def Shader "{MAP_NAMES[name]["name"]}"
	{{
		uniform token info:id = "{MAP_NAMES[name]["id"]}"
		asset inputs:file = @{properties["filename"]}@
		{MAP_NAMES[name]["type"]} outputs:out
	}}
	'''

	if MAP_NAMES[name]['name'] == 'Normal':
		output = f'''
	def Shader "mtlxnormalmap1"
	{{
		uniform token info:id = "ND_normalmap"
		vector3f inputs:in.connect = </{MATERIAL["name"]}/Normal.outputs:out>
		float inputs:scale = {MATERIAL["normal_amount"]}
		vector3f outputs:out
	}}
	''' + output 

	return output


def build_usd():
	shaders = ''
	shader_connections = ''
	for k,v in MATERIAL.items():
		if isinstance(v, dict):
			shader_info = MAP_NAMES[k]
			shaders += usd_shader(k, v)
			shader_connections += f'		{shader_info["type"]} inputs:{shader_info["port"]}.connect = </{MATERIAL["name"]}/{"mtlxnormalmap1" if shader_info["name"] == "Normal" else shader_info["name"]}.outputs:out>\n' 

	output = f'''#usda 1.0

def Material "{MATERIAL["name"]}" (
	prepend inherits = </__class_mtl__/{MATERIAL["name"]}>
)
{{
	token outputs:mtlx:surface.connect = </{MATERIAL["name"]}/mtlxstandard_surface.outputs:out>

	def Shader "mtlxstandard_surface"
	{{
		uniform token info:id = "ND_standard_surface_surfaceshader"
		float inputs:base
		color3f inputs:base_color = {MATERIAL["Diffuse"] if isinstance(MATERIAL["Diffuse"], str) else (0,0,0)}
		float inputs:coat
		float inputs:coat_roughness
		float inputs:emission
		color3f inputs:emission_color
		float inputs:metalness = {MATERIAL["reflection_metalness"] if isinstance(MATERIAL["reflection_metalness"], str) else 0}
		float inputs:specular
		color3f inputs:specular_color = {MATERIAL["Reflection"]}
		float inputs:specular_IOR = {MATERIAL["refraction_ior"]}
		float inputs:specular_roughness = {MATERIAL["reflection_glossiness"] if isinstance(MATERIAL["reflection_glossiness"], str) else 0}
		float inputs:transmission = {"0" if MATERIAL["Refraction"] == "(0.0,0.0,0.0)" else 1}
		color3f inputs:transmission_color = {MATERIAL["refraction_fogColor"]}
		float inputs:transmission_depth = {"1.0" if MATERIAL["refraction_fogMult"] == "0.0" else MATERIAL["refraction_fogMult"]}
{shader_connections}
		token outputs:out
	}}

	{shaders}
}}
'''
	return output


def convert_mdl(path):
	filename, ext = os.path.splitext(path)
	if ext != '.mdl':
		raise TypeError(f'Not an mdl file')

	print(f"Converting {os.path.basename(path)}")

	global MDL
	global line
	global MATERIAL
	MDL = read_file(path)

	# Get material name
	line = next(MDL)
	while (match := re.match('export material (.*)\(\*\)', line)) is None:
		line = next(MDL)
	
	material_name = match.group(1)
	# print(material_name)
	
	while line != '= ::templates::vray_materials::VRayMtl(':
		line = next(MDL)
	
	line = next(MDL)
	
	MATERIAL['name'] = material_name
	MATERIAL.update(get_properties())

	# for k,v in MATERIAL.items():
	# 	print(k,v)

	usd = build_usd()
	# print(usd)
	
	with open(filename + '.usd', 'w') as file:
		file.write(usd)


def main(path):
	if not os.path.isdir(path):
		convert_mdl(path)
	else:
		for file in os.listdir(path):
			if file.endswith('.mdl'):
				convert_mdl(os.path.join(path, file))

if __name__ == "__main__":
	if len(sys.argv) > 1:
		main(sys.argv[1])
	else:
		print("Pass the path to an MDL file or directory of MDL files.")


