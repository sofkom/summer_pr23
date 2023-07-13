import boto3
import os
import sys
import configparser
import argparse

BUCKET = ''


def client_from_config() -> boto3.Session.client:
    try:
        cfg_file = open(f'{os.environ["HOME"].replace(chr(92), "/")}/.config/cloudphoto/cloudphotorc')
    except OSError:
        print("Не удалось прочитать конфигурационный файл", file=sys.stderr)
        sys.exit(os.EX_CONFIG)

    cfg = configparser.ConfigParser()  # creating parser to get configuration info
    cfg.read_file(cfg_file)
    try:
        bucket = cfg['default']['bucket']
        aws_access_key_id = cfg['default']['aws_access_key_id']
        aws_secret_access_key = cfg['default']['aws_secret_access_key']
        region = cfg['default']['region']
        endpoint_url = cfg['default']['endpoint_url']
    except KeyError as err:
        print(f"Не найден параметр {err}")
        sys.exit(os.EX_CONFIG)

    session = boto3.session.Session()
    client = session.client(
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        region_name=region,
        service_name='s3',
        endpoint_url=endpoint_url
    )
    global BUCKET
    BUCKET = bucket

    return client


def my_parser() -> argparse.ArgumentParser:
    """
    A method to create parser for CLI
    :return: parser with made commands
    """
    parser = argparse.ArgumentParser()  # creating empty parser
    sub_parser = parser.add_subparsers(dest='command', required=True)

    upload_command = sub_parser.add_parser('upload', help='Uploading photos')
    upload_command.add_argument('-a', '--album', type=str, dest='album', required=True)  # adding argument to command
    upload_command.add_argument('-p', '--path', type=str, dest='path', required=True)

    delete_command = sub_parser.add_parser('delete', help='Deleting photos')
    delete_command.add_argument('-a', '--album', type=str, dest='album', required=True)
    delete_command.add_argument('-p', '--path', type=str, dest='path', required=True)

    list_albums_command = sub_parser.add_parser('list-albums', help='Showing all albums')

    generate_site_command = sub_parser.add_parser('generate-site', help='Generating website with albums')
    init_command = sub_parser.add_parser('init', help='Initialize configuration interactively')

    return parser

def init() -> None:
    """
    A function to initialize the configuration file interactively.
    :return: None
    """
    cfg = configparser.ConfigParser()


    config_dir = f'{os.environ["HOME"].replace(chr(92), "/")}/.config/cloudphoto'
    cfg_file = f'{config_dir}/cloudphotorc'

    if os.path.exists(cfg_file):
        cfg.read(cfg_file)

    aws_access_key_id = input("Enter AWS Access Key ID (press enter to keep existing value): ")
    aws_secret_access_key = input("Enter AWS Secret Access Key (press enter to keep existing value): ")
    bucket = input("Enter the name of the bucket (press enter to keep existing value): ")

    if aws_access_key_id:
        cfg['default']['aws_access_key_id'] = aws_access_key_id
    if aws_secret_access_key:
        cfg['default']['aws_secret_access_key'] = aws_secret_access_key
    if bucket:
        cfg['default']['bucket'] = bucket


    os.makedirs(config_dir, exist_ok=True)


    with open(cfg_file, 'w') as file:
        cfg.write(file)
def upload(album: str, path: str) -> None:

    if not os.path.exists(path) or not os.path.isdir(path):
        print(f'No such path or path is not directory: {path}')
        return
    files = os.listdir(path)
    pictures = list(filter(lambda file: file.endswith(('.jpg', '.jpeg')), files))  # getting only photos
    for picture in pictures:
        s3.upload_file(Bucket=BUCKET, Key=f'{album}/{picture}', Filename=path + '/' + picture)
    if len(pictures) == 0:
        s3.put_object(Bucket=BUCKET, Key=f'{album}/')
    print('Successfully uploaded')


def delete(album: str, path: str) -> None:

    if not os.path.exists(path) or not os.path.isdir(path):
        print(f'No such path or path is not a directory: {path}')
        return

    files = os.listdir(path)  # Getting all files from the path
    pictures = list(filter(lambda file: file.endswith(('.jpg', '.jpeg')), files))  # Getting only photos

    for picture in pictures:

        s3.delete_object(Bucket=BUCKET, Key=f'{album}/{picture}')

    print('Deletion successful')


def list_albums() -> list:
    """
    A method to get all albums from Bucket
    :return: list containig albums
    """

    response = filter(lambda elem: len(elem['Key']) > 5, s3.list_objects_v2(Bucket=BUCKET)['Contents'])
    pictures_info = filter(lambda res: res["Key"].endswith(('.jpg', '.jpeg')), response)
    albums_set = set()
    for picture in pictures_info:
        name = picture['Key']
        albums_set.add(name[:name.rfind('/')])
    print('Albums:', ', '.join(list(albums_set)))
    return list(albums_set)


def generate_site() -> None:

    # index page template
    first_page = f"""<!doctype html>
    <html>
        <head>
            <title>PhotoArchive</title>
        </head>
    <body>
        <h1>PhotoArchive</h1>
        <ul>
        </ul>
    </body>
    """
    other_page = """<!doctype html>
    <html>
        <head>
            <link rel="stylesheet" type="text/css" href="https://cdnjs.cloudflare.com/ajax/libs/galleria/1.6.1/themes/classic/galleria.classic.min.css" />
            <style>
                .galleria{ width: 960px; height: 540px; background: #000 }
            </style>
            <script src="https://ajax.googleapis.com/ajax/libs/jquery/3.6.0/jquery.min.js"></script>
            <script src="https://cdnjs.cloudflare.com/ajax/libs/galleria/1.6.1/galleria.min.js"></script>
            <script src="https://cdnjs.cloudflare.com/ajax/libs/galleria/1.6.1/themes/classic/galleria.classic.min.js"></script>
        </head>
        <body>
            <div class="galleria">
            </div>
            <script>
                (function() {
                    Galleria.run('.galleria');
                }());
            </script>
        </body>
    </html>
    """
    for album in list_albums():
        link = f'\n\t\t\t<li><a href="website/{album}.html">{album}</a></li>'
        first_page = first_page[:first_page.find('<ul>') + 4] + link + first_page[first_page.find('<ul>') + 4:]
        pictures = list_photos(album)
        album_page = other_page[:]
        for picture in pictures:
            photo_link = f'\n\t\t\t\t<img src="https://storage.yandexcloud.net/{BUCKET}/{album}/{picture}">'
            album_page = album_page[:album_page.find('class="galleria">') + 17] + photo_link + album_page[
                                                                                               album_page.find(
                                                                                                   'class="galleria">') + 17:]
        s3.put_object(Bucket=BUCKET, Key=f'website/{album}.html', Body=album_page)
    s3.put_object(Bucket=BUCKET, Key='index.html', Body=first_page)
    s3.put_bucket_acl(Bucket=BUCKET, ACL='public-read')
    s3.put_bucket_website(Bucket=BUCKET, WebsiteConfiguration={'IndexDocument': {'Suffix': 'index.html'}})
    print(f'https://{BUCKET}.website.yandexcloud.net')


func_name = {
    'upload': upload,
    'delete': delete,
    'lists': list_albums,
    'mksite': generate_site,
    'init': init
}

if __name__ == "__main__":
    s3 = client_from_config()
    arg_parser = my_parser()
    args = arg_parser.parse_args()
    if args.command == 'lists' or args.command == 'mksite':
        func_name[args.command]()
    else:
        func_name[args.command](args.album, args.path)