import os, sys, time, json, resource, zipfile, zlib, struct, io
sys.path.insert(0, os.path.join(os.getcwd(), 'nofos'))
os.environ['DJANGO_SETTINGS_MODULE'] = 'bloom_nofos.settings'
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['DEBUG'] = 'False'
os.environ['IS_PROD'] = 'False'
sys.argv.append('test')
import django
django.setup()
from django.conf import settings
settings.ALLOWED_HOSTS = ['testserver', 'localhost']
settings.CONSTANCE_BACKEND = 'constance.backends.memory.MemoryBackend'
from django.test.utils import setup_test_environment
from django.core.management import call_command
setup_test_environment()
call_command('migrate', verbosity=0)
from django.test import Client
from django.core.files.uploadedfile import SimpleUploadedFile
from users.models import BloomUser
from nofos.models import Nofo, Subsection, ImportAttempt
from constance.test import override_config

def chunk(kind, data):
    return struct.pack('!I', len(data)) + kind + data + struct.pack('!I', zlib.crc32(kind+data)&0xffffffff)

w=h=3950
raw=b''.join(b'\0'+os.urandom(w*3) for _ in range(h))
png=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('!IIBBBBB',w,h,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(raw,1))+chunk(b'IEND',b'')
del raw
target=45*1024*1024
document='''<?xml version="1.0" encoding="UTF-8"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"><w:body><w:p><w:r><w:t>Opportunity name: Synthetic 45 MiB NOFO</w:t></w:r></w:p><w:p><w:r><w:t>Opportunity number: SIZE-PROBE-001</w:t></w:r></w:p><w:p><w:r><w:t>Opdiv: CDC</w:t></w:r></w:p><w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>Step 1: Review the Opportunity</w:t></w:r></w:p><w:p><w:pPr><w:pStyle w:val="Heading2"/></w:pPr><w:r><w:t>Eligibility Information</w:t></w:r></w:p><w:p><w:r><w:t>Synthetic import size verification.</w:t></w:r></w:p><w:p><w:r><w:drawing><wp:inline><wp:extent cx="914400" cy="914400"/><wp:docPr id="1" name="Synthetic image" descr="Random test image"/><a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:pic><pic:nvPicPr><pic:cNvPr id="0" name="probe.png"/><pic:cNvPicPr/></pic:nvPicPr><pic:blipFill><a:blip r:embed="rIdProbe"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill><pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="914400" cy="914400"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr></pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r></w:p></w:body></w:document>'''
fixture='nofos/nofos/fixtures/docx/lists.docx'
out=io.BytesIO()
with zipfile.ZipFile(fixture) as src, zipfile.ZipFile(out,'w',compression=zipfile.ZIP_STORED) as dst:
    for entry in src.infolist():
        if entry.filename=='word/document.xml': data=document.encode()
        elif entry.filename=='word/_rels/document.xml.rels':
            data=src.read(entry).replace(b'</Relationships>',b'<Relationship Id="rIdProbe" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/probe.png"/></Relationships>')
        elif entry.filename=='[Content_Types].xml':
            data=src.read(entry)
            if b'Extension="png"' not in data: data=data.replace(b'</Types>',b'<Default Extension="png" ContentType="image/png"/></Types>')
        else: data=src.read(entry)
        dst.writestr(entry.filename,data)
    dst.writestr('word/media/probe.png',png)
del png
# Small unreferenced package part adjusts the valid image-heavy fixture to exactly 45 MiB.
padding_name='size-padding.bin'
padding=target-len(out.getvalue())-(30+46+2*len(padding_name))
assert padding>=0, padding
with zipfile.ZipFile(out,'a',compression=zipfile.ZIP_STORED) as dst: dst.writestr(padding_name,b'0'*padding)
payload=out.getvalue()
assert len(payload)==target,(len(payload),target)
with zipfile.ZipFile(io.BytesIO(payload)) as z: assert z.testzip() is None
user=BloomUser.objects.create_user(email='probe@example.com',password='synthetic-only',force_password_reset=False,group='bloom')
client=Client();client.force_login(user)
upload=SimpleUploadedFile('synthetic-45MiB.docx',payload,content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
start=time.perf_counter()
with override_config(WORD_IMPORT_STRICT_MODE=False):
    response=client.post('/nofos/import',{'nofo-import':upload})
elapsed=time.perf_counter()-start
result={'bytes':len(payload),'MiB':len(payload)/1024**2,'padding_bytes':padding,'elapsed_seconds':round(elapsed,3),'status':response.status_code,'location':response.get('Location'),'saved_nofos':Nofo.objects.count(),'saved_subsections':Subsection.objects.count(),'peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
result['image_preserved']=any('data:image/png;base64,' in b for b in Subsection.objects.values_list('body',flat=True))
result['attempts']=list(ImportAttempt.objects.values('error_code'))
print('PROBE_RESULT '+json.dumps(result))
assert response.status_code==302 and result['saved_nofos']==1 and result['image_preserved'],result
