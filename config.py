import json, re


def get_config():
    config_file = open("config.json")
    config = config_file.read()
    (config, count) = re.subn("//( |\w)*\n", "", config)
    config = json.loads(config)
    return config


if __name__ == '__main__':
    x = get_config()
    print(x)
    print x['word_size']
