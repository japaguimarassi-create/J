#!/usr/bin/env python3
import argparse, hashlib, json, os, re, struct, sys, zipfile
from collections import Counter
from pathlib import Path

ISSUES=[]
CHECKS=[]
def check(name, ok, detail, severity='ERROR'):
    CHECKS.append({'check':name,'passed':bool(ok),'detail':detail})
    if not ok: ISSUES.append({'severity':severity,'check':name,'detail':detail})

def audit(path):
    p=Path(path)
    if not p.is_file():
        check('file_exists',False,f'Arquivo não encontrado: {p}')
        return
    check('file_exists',True,f'{p} ({p.stat().st_size} bytes)')
    digest=hashlib.sha256(p.read_bytes()).hexdigest()
    check('sha256',True,digest,'INFO')
    try:
        z=zipfile.ZipFile(p)
        bad=z.testzip()
        check('zip_integrity',bad is None, f'CRC válido' if bad is None else f'Primeiro membro corrompido: {bad}')
        names=z.namelist(); counts=Counter(names)
        duplicates=[n for n,c in counts.items() if c>1]
        check('duplicate_entries',not duplicates, ', '.join(duplicates[:20]))
        manifest=''
        if 'META-INF/MANIFEST.MF' in names:
            manifest=z.read('META-INF/MANIFEST.MF').decode('utf-8','replace')
        check('manifest',bool(manifest),'Manifest presente' if manifest else 'META-INF/MANIFEST.MF ausente')
        check('forge_mod_descriptor_at_root','META-INF/mods.toml' in names,
              'META-INF/mods.toml está na raiz do JAR' if 'META-INF/mods.toml' in names
              else 'mods.toml deve estar em META-INF/mods.toml')
        if 'META-INF/mods.toml' in names:
            descriptor=z.read('META-INF/mods.toml').decode('utf-8','replace')
            required_tokens=[
                ('javafml_loader','modLoader="javafml"'),
                ('loader_major_47','loaderVersion="[47,)"'),
                ('mod_id_voxmobs','modId="voxmobs"'),
                ('minecraft_1_20_1','versionRange="[1.20.1,1.20.2)"'),
                ('forge_major_47','versionRange="[47,)"')
            ]
            for check_name, token in required_tokens:
                check(check_name, token in descriptor,
                      f'{token} presente' if token in descriptor else f'Metadata não contém {token}')
        classes=[n for n in names if n.endswith('.class')]
        check('compiled_classes',bool(classes),f'{len(classes)} arquivos .class encontrados')
        if classes:
            majors=Counter()
            malformed=[]
            for n in classes:
                b=z.read(n)
                if len(b)<8 or b[:4]!=b'\xca\xfe\xba\xbe': malformed.append(n); continue
                majors[struct.unpack('>H',b[6:8])[0]]+=1
            check('class_bytecode',not malformed,f'Versões major: {dict(majors)}; inválidos: {malformed[:10]}')
            check('java_17_bytecode',all(v<=61 for v in majors),f'Java 17 = major 61; detectado: {dict(majors)}')
        tomls=[n for n in names if n.endswith('mods.toml')]
        check('forge_mod_metadata',bool(tomls),f'Metadata encontrada: {tomls}')
        if tomls:
            data='\n'.join(z.read(n).decode('utf-8','replace') for n in tomls)
            check('metadata_placeholders',not bool(re.search(r'\$\{[^}]+\}',data)), 'Sem placeholders não resolvidos' if not re.search(r'\$\{[^}]+\}',data) else 'Há placeholders ${...} não resolvidos')
            check('mod_id', 'modId="voxmobs"' in data or "modId='voxmobs'" in data, 'modId voxmobs presente')
        source_entries=[n for n in names if n.endswith('.java')]
        source_only=('SOURCE-ARCHIVE-NOT-INSTALLABLE' in manifest or (source_entries and not classes))
        check('not_source_only',not source_only,'JAR contém bytecode compilado' if not source_only else 'Este JAR é somente fonte e não pode ser instalado como mod Forge')
        check('mod_main_class',any(n.endswith('/VoxMobs.class') for n in classes), 'Classe principal VoxMobs.class presente' if any(n.endswith('/VoxMobs.class') for n in classes) else 'Classe principal compilada VoxMobs.class ausente')
        jarjar_path='META-INF/jarjar/metadata.json'
        check('jarjar_metadata',jarjar_path in names,
              'Manifesto Jar-in-Jar presente' if jarjar_path in names else 'Manifesto Jar-in-Jar ausente')
        if jarjar_path in names:
            try:
                jarjar=json.loads(z.read(jarjar_path).decode('utf-8'))
                bundled={(x.get('identifier',{}).get('group'),x.get('identifier',{}).get('artifact'),x.get('version',{}).get('artifactVersion')):x.get('path') for x in jarjar.get('jars',[])}
                for group,artifact,version in [
                    ('com.alphacephei','vosk','0.3.45'),
                    ('net.java.dev.jna','jna','5.7.0')
                ]:
                    entry=bundled.get((group,artifact,version))
                    check('jarjar_'+artifact, bool(entry) and entry in names,
                          f'{artifact} {version} indexado e incluído' if entry and entry in names
                          else f'{artifact} {version} ausente do índice Jar-in-Jar ou do JAR')
            except Exception as e:
                check('jarjar_metadata_json',False,f'Metadata inválida: {e}')
        z.close()
    except Exception as e:
        check('jar_open',False,f'{type(e).__name__}: {e}')
    return {'file':str(p),'size_bytes':p.stat().st_size,'sha256':digest,'checks':CHECKS,'issues':ISSUES,'summary':{'passed':sum(x['passed'] for x in CHECKS),'failed':sum(not x['passed'] for x in CHECKS),'errors':sum(x['severity']=='ERROR' for x in ISSUES)}}

if __name__=='__main__':
    ap=argparse.ArgumentParser(description='Auditoria estática e estrutural de JAR Java/Forge')
    ap.add_argument('jar'); ap.add_argument('--json',default='reports/jar-audit.json'); ap.add_argument('--markdown',default='reports/jar-audit.md')
    a=ap.parse_args(); result=audit(a.jar)
    Path(a.json).parent.mkdir(parents=True,exist_ok=True)
    Path(a.json).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    lines=['# Relatório de auditoria JAR','',f"**Arquivo:** `{result.get('file','')}`  ",f"**SHA-256:** `{result.get('sha256','')}`  ",f"**Resumo:** {result.get('summary',{})}",'','## Verificações']
    for c in result.get('checks',[]): lines.append(f"- {'PASS' if c['passed'] else 'FAIL'} — **{c['check']}**: {c['detail']}")
    lines+=['','## Problemas']
    lines += [f"- **{i['severity']}** — {i['check']}: {i['detail']}" for i in result.get('issues',[])] or ['Nenhum problema estrutural encontrado.']
    Path(a.markdown).write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps(result.get('summary',{}),ensure_ascii=False))
    sys.exit(1 if result.get('summary',{}).get('errors',0) else 0)
