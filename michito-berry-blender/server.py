#!/usr/bin/env python3
"""Michito Berry Blender v5 - remote Jessica selector, DM-operated show, TV and phones."""
import asyncio, io, json, math, os, secrets, socket, time
from collections import Counter
from pathlib import Path
from aiohttp import web, WSMsgType
import qrcode

ROOT=Path(__file__).parent
BERRIES={
 'cheri':{'name':'Cheri','flavor':'Spicy','color':'Red','smoothness':25},
 'chesto':{'name':'Chesto','flavor':'Dry','color':'Blue','smoothness':25},
 'pecha':{'name':'Pecha','flavor':'Sweet','color':'Pink','smoothness':25},
 'rawst':{'name':'Rawst','flavor':'Bitter','color':'Green','smoothness':25},
 'aspear':{'name':'Aspear','flavor':'Sour','color':'Yellow','smoothness':25},
 'oran':{'name':'Oran','flavor':'Spicy / Dry / Sweet / Bitter / Sour','color':'Purple','smoothness':20},
 'sitrus':{'name':'Sitrus','flavor':'Spicy / Dry / Sweet / Bitter / Sour','color':'Purple','smoothness':20}}
# In RSE, preference is from Nature, never species. These Natures are *sample campaign assignments*.
POKEMON={
 'miraidon':{'name':'Miraidon','nickname':'Vega','ids':[1008],'nature':'Modest','likes':'Dry','dislikes':'Spicy'},
 'plusleminun':{'name':'Plusle & Minun','nickname':'Poppy & Pippa','ids':[311,312],'nature':'Jolly / Timid','likes':'Sweet','dislikes':'Dry / Spicy'},
 'boltund':{'name':'Boltund','nickname':'Dash','ids':[836],'nature':'Adamant','likes':'Spicy','dislikes':'Dry'},
 'luxray':{'name':'Luxray','nickname':'Lex','ids':[405],'nature':'Calm','likes':'Bitter','dislikes':'Spicy'},
 'raika':{'name':'Raika','nickname':'Kira','ids':[],'image':'https://i.imgur.com/hxRIh7T.png','nature':'Impish','likes':'Sour','dislikes':'Dry'} }

COLORS=['#f7a7d7','#75d8ff','#ffd36b','#a1f2b7','#bd9df9','#ffad7d','#f5e7ab']
FLAVOR_BERRY={'Spicy':'cheri','Dry':'chesto','Sweet':'pecha','Bitter':'rawst','Sour':'aspear'}
ROOMS={}; TOTAL_REVOLUTIONS=12; PRACTICE_REVOLUTIONS=3

def lan_ip():
 s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
 try:s.connect(('1.1.1.1',80));return s.getsockname()[0]
 except OSError:return '127.0.0.1'
 finally:s.close()

class Room:
 def __init__(self,code):
  self.code=code;self.owner_key=secrets.token_urlsafe(18);self.jessica_key=secrets.token_urlsafe(18)
  self.owners=set();self.jessicas=set();self.stages=set();self.clients={};self.players={}
  self.status='lobby';self.show_round=0;self.pokemon_id=None;self.result=None
  self.events=[];self.task=None;self.angle=0.;self.revolution=0;self.speed=0.;self.hits={};self.practice=False;self.used_pokemon=set()
 def target(self):return POKEMON.get(self.pokemon_id)
 def player_list(self):return list(self.players.values())
 def data(self,role):
  # HIDE selected Pokémon and favorite flavor from players/stage until AFTER the block reveal.
  private=role in ('owner','jessica') or self.status=='pokemon_result'
  obj={'type':'state','room':self.code,'status':self.status,'showRound':self.show_round,
   'players':self.player_list(),'events':self.events[-14:], 'result':self.result,
   'selected':self.pokemon_id is not None,'hint':('Make a Pokéblock with a '+self.target()['likes'].lower()+' flavor!' if self.target() and self.status in ('choosing','practice','blending','block_result') else None),'wantedFlavor':self.target()['likes'] if self.target() and self.status in ('choosing','practice','blending','block_result') else None,'berryGuide':[{'id':k,'name':v['name'],'flavor':v['flavor']} for k,v in BERRIES.items()],'pokemon':self.target() if private else None,
   'pokemonId':self.pokemon_id if private else None,
   'revolution':self.revolution,'totalRevolutions':PRACTICE_REVOLUTIONS if self.practice else TOTAL_REVOLUTIONS,
   'angle':self.angle,'speed':self.speed,'practice':self.practice,'readyCount':sum(p['ready'] for p in self.players.values())}
  if role in ('owner','jessica'):obj['pokemonList']=[dict(id=k,used=k in self.used_pokemon,**v) for k,v in POKEMON.items()]
  if role=='owner':obj['jessicaKey']=self.jessica_key
  return obj
 async def publish(self):
  for role,socks in [('owner',self.owners),('jessica',self.jessicas),('stage',self.stages),('player',set(self.clients.values()))]:
   payload=json.dumps(self.data(role))
   await asyncio.gather(*(w.send_str(payload) for w in list(socks) if not w.closed),return_exceptions=True)
 async def broadcast(self,event):
  sockets=list(self.owners)+list(self.jessicas)+list(self.stages)+list(self.clients.values())
  msg=json.dumps(event)
  await asyncio.gather(*(w.send_str(msg) for w in sockets if not w.closed),return_exceptions=True)
 async def new_round(self):
  if self.status not in ('lobby','pokemon_result'):return
  self.show_round+=1;self.status='waiting_jessica';self.pokemon_id=None;self.result=None;self.events=[]
  self.revolution=0;self.speed=0;self.angle=0;self.practice=False
  for p in self.players.values():p.update(berry=None,ready=False,score=0,hits=[])
  await self.publish()
 async def select(self,key):
  if self.status!='waiting_jessica' or key not in POKEMON or key in self.used_pokemon:return
  self.pokemon_id=key;self.used_pokemon.add(key);self.status='choosing';await self.publish()
 async def practice_game(self):
  if self.status!='choosing' or not self.players:return
  await self.start(True)
 async def start(self,practice=False):
  if self.status!='choosing' or not self.players or not self.pokemon_id:return
  if not practice and not all(p['ready'] for p in self.players.values()):return
  if self.task and not self.task.done():self.task.cancel()
  self.practice=practice;self.status='practice' if practice else 'blending';self.events=[]
  self.revolution=0;self.speed=0.25;self.angle=math.pi/max(1,len(self.players)) # between two markers!
  self.hits={};self.result=None
  if not practice:
   for p in self.players.values():p.update(score=0,hits=[])
  await self.publish();self.task=asyncio.create_task(self.spin());
 async def spin(self):
  # Continuous spinning, accelerating from good/perfect hits. One attempt/player/revolution.
  try:
   await self.broadcast({'type':'countdown','seconds':3});await asyncio.sleep(3)
   laps=PRACTICE_REVOLUTIONS if self.practice else TOTAL_REVOLUTIONS
   total_angle=self.angle;last=time.monotonic();last_pub=0
   while self.revolution<laps and self.status in ('practice','blending'):
    now=time.monotonic();dt=min(.12,now-last);last=now
    # Smooth baseline acceleration plus hit-based bonus.
    base=0.32+0.018*self.revolution
    self.speed=min(1.55,max(self.speed,base))
    total_angle+=self.speed*2*math.pi*dt
    self.angle=total_angle%(2*math.pi)
    new_rev=int((total_angle-math.pi/max(1,len(self.players)))/(2*math.pi))
    if new_rev>self.revolution:
     for completed in range(self.revolution,min(new_rev,laps)):
      for pid,p in self.players.items():
       if (completed,pid) not in self.hits:
        self.hits[(completed,pid)]='MISS'
        if not self.practice:p['hits'].append('MISS')
        self.events.append(f"{p['name']}: MISS (no press)")
        await self.broadcast({'type':'hit','player':pid,'name':p['name'],'outcome':'MISS','score':p['score'],'practice':self.practice,'revolution':completed,'automatic':True})
     self.revolution=new_rev
     await self.publish()
    if now-last_pub>.035:
     await self.broadcast({'type':'tick','angle':self.angle,'revolution':self.revolution,'speed':self.speed,'running':True})
     last_pub=now
    await asyncio.sleep(.018)
   self.revolution=laps;await self.broadcast({'type':'tick','angle':self.angle,'revolution':laps,'speed':0,'running':False})
   if self.practice:self.status='choosing';self.events=[];self.practice=False
   else:self.finish();self.status='block_result'
   await self.publish()
  except asyncio.CancelledError:pass
 def finish(self):
  counts=Counter(p['berry'] for p in self.players.values() if p['berry'])
  # Seven-player party rule: participants may repeat the target-flavor Berry; unlike
  # authentic Gen III 2-4 participant blending, duplicates do NOT force a black block.
  # This keeps flavor clues solvable with seven people and five basic berries.
  favorite=self.target()['likes'];favorite_berry=FLAVOR_BERRY[favorite]
  favorite_count=counts.get(favorite_berry,0)
  n=sum(counts.values());minimum=max(1,math.ceil(n/2))
  success=bool(n) and favorite_count>=minimum
  # Let the majority of flavor choices decide the colored Pokeblock.
  dominant=max(counts.values(),default=0)
  leaders=[k for k,v in counts.items() if v==dominant]
  primary=leaders[0] if len(leaders)==1 else None
  color=BERRIES[primary]['color'] if primary else 'Purple'
  flavor=BERRIES[primary]['flavor'] if primary else 'Mixed'
  total=sum(p['score'] for p in self.players.values());maxscore=len(self.players)*TOTAL_REVOLUTIONS*2
  ratio=total/maxscore if maxscore else 0
  level=max(1,round(10+ratio*40));feel=max(1,25-max(2,len(self.players)))
  quality='EXCELLENT' if ratio>=.8 else 'GREAT' if ratio>=.6 else 'GOOD' if ratio>=.3 else 'ROUGH'
  self.result={'color':color,'level':level,'feel':feel,'quality':quality,'berries':dict(counts),
   'flavor':flavor,'recipeSuccess':success,'score':total,'maxScore':maxscore,
   'targetCount':favorite_count,'targetMinimum':minimum,
   'ranking':sorted([{'name':p['name'],'score':p['score'],'color':p['color']} for p in self.players.values()],key=lambda p:-p['score']),
   'note':'Classic Berry flavor identities; seven-player majority recipe, Level, Feel and scoring are campaign adaptations.'}
 async def press(self,pid):
  if self.status not in ('practice','blending') or pid not in self.players or self.revolution>=(PRACTICE_REVOLUTIONS if self.practice else TOTAL_REVOLUTIONS):return
  current=self.revolution;key=(current,pid)
  if key in self.hits:return
  ids=list(self.players);index=ids.index(pid);n=len(ids)
  target=index*math.tau/n;dist=abs((self.angle-target+math.pi)%(math.tau)-math.pi)
  space=math.tau/n;outcome='PERFECT' if dist<=space*.18 else 'GOOD' if dist<=space*.39 else 'MISS'
  pts={'PERFECT':2,'GOOD':1,'MISS':0}[outcome];self.hits[key]=outcome
  p=self.players[pid]
  if not self.practice:p['score']+=pts;p['hits'].append(outcome)
  if outcome=='PERFECT':self.speed=min(1.55,self.speed+.035)
  elif outcome=='GOOD':self.speed=min(1.55,self.speed+.012)
  else:self.speed=max(.32,self.speed-.018)
  self.events.append(f"{p['name']}: {outcome}"+(" (practice)" if self.practice else f" +{pts}"))
  await self.broadcast({'type':'hit','player':pid,'name':p['name'],'outcome':outcome,'score':p['score'],'practice':self.practice,'revolution':current})
  await self.publish()
 async def reveal(self):
  if self.status=='block_result':self.status='pokemon_result';await self.publish()
 async def reset(self):
  if self.task and not self.task.done():self.task.cancel()
  self.status='lobby';self.show_round=0;self.pokemon_id=None;self.result=None;self.events=[]
  self.revolution=0;self.speed=0;self.practice=False;self.used_pokemon=set()
  for p in self.players.values():p.update(berry=None,ready=False,score=0,hits=[])
  await self.publish()

async def index(request):return web.FileResponse(ROOT/'static'/'index.html',headers={'Cache-Control':'no-store'})
async def qr(request):
 code=request.match_info['code'];base=f'{request.scheme}://{request.host}'
 if request.host.startswith(('localhost:','127.0.0.1:')):base=f'http://{lan_ip()}:{request.app["port"]}'
 img=qrcode.make(f'{base}/play?room={code}');bio=io.BytesIO();img.save(bio,format='PNG')
 return web.Response(body=bio.getvalue(),content_type='image/png')
async def ws_handler(request):
 ws=web.WebSocketResponse(heartbeat=20);await ws.prepare(request)
 role=request.query.get('role','player');code=request.query.get('room','').upper().strip();key=request.query.get('key','')
 if role=='owner' and not code:code=''.join(secrets.choice('ABCDEFGHJKLMNPQRSTUVWXYZ23456789') for _ in range(4))
 room=ROOMS.get(code);created=False
 if role=='owner' and room is None:room=ROOMS[code]=Room(code);created=True
 if room is None:await ws.send_json({'type':'error','message':'Room not found.'});await ws.close();return ws
 if role=='owner' and (key and not secrets.compare_digest(key,room.owner_key) or not key and not created):
  await ws.send_json({'type':'error','message':'DM key required. Use the original controller link.'});await ws.close();return ws
 if role=='jessica' and not secrets.compare_digest(key,room.jessica_key):
  await ws.send_json({'type':'error','message':'Invalid Jessica invite link.'});await ws.close();return ws
 if role not in ('owner','jessica','stage','player'):await ws.close();return ws
 pid=None
 if role=='owner':room.owners.add(ws)
 elif role=='jessica':room.jessicas.add(ws)
 elif role=='stage':room.stages.add(ws)
 else:
  token=request.query.get('token','')
  if token in room.players:pid=token
  elif len(room.players)>=7 or room.status in ('practice','blending'):
   await ws.send_json({'type':'error','message':'Room full or round in progress.'});await ws.close();return ws
  else:
   pid=secrets.token_urlsafe(12)
   used={p['color'] for p in room.players.values()}
   color=next(c for c in COLORS if c not in used)
   room.players[pid]={'id':pid,'name':f'Trainer {len(room.players)+1}','berry':None,'ready':False,'score':0,'hits':[],'color':color}
  room.clients[pid]=ws
 await ws.send_json({'type':'hello','role':role,'room':code,'id':pid,'ownerKey':room.owner_key if role=='owner' else None})
 await room.publish()
 try:
  async for msg in ws:
   if msg.type!=WSMsgType.TEXT:continue
   try:d=json.loads(msg.data)
   except (ValueError,TypeError):continue
   action=d.get('action')
   if role=='owner':
    if action=='begin_round':await room.new_round()
    elif action=='practice':await room.practice_game()
    elif action=='start':await room.start()
    elif action=='reveal':await room.reveal()
    elif action=='reset':await room.reset()
    elif action=='remove' and room.status not in ('practice','blending'):
     rid=d.get('id')
     if rid in room.players:
      room.players.pop(rid);w=room.clients.pop(rid,None)
      if w:await w.close()
      await room.publish()
   elif role=='jessica':
    if action=='pokemon':await room.select(d.get('id'))
   elif role=='player' and pid in room.players:
    p=room.players[pid]
    if action=='join' and room.status not in ('practice','blending'):
     name=str(d.get('name','')).strip()[:22]
     if name:p['name']=name
     await room.publish()
    elif action=='berry' and room.status=='choosing' and d.get('berry') in BERRIES:
     if not p['ready']:
      p['berry']=d['berry'];await room.publish()
    elif action=='ready' and room.status=='choosing' and p['berry'] in BERRIES:
     p['ready']=True;await room.publish()
    elif action=='unready' and room.status=='choosing':
     p['ready']=False;await room.publish()
    elif action=='press':await room.press(pid)
 finally:
  if role=='owner':room.owners.discard(ws)
  elif role=='jessica':room.jessicas.discard(ws)
  elif role=='stage':room.stages.discard(ws)
  elif room.clients.get(pid) is ws:room.clients.pop(pid,None)
  if room.owners or room.jessicas or room.stages or room.clients:await room.publish()
 return ws

def main():
 import argparse
 ap=argparse.ArgumentParser();ap.add_argument('--port',type=int,default=int(os.getenv('PORT','8765')));args=ap.parse_args()
 app=web.Application();app['port']=args.port
 for path in ('/','/control','/jessica','/stage','/play'):app.router.add_get(path,index)
 app.router.add_get('/qr/{code}',qr);app.router.add_get('/ws',ws_handler);app.router.add_static('/static',ROOT/'static')
 print(f'\nMICHITO BERRY BLENDER v5\nDM: http://localhost:{args.port}/control\nTV: use the stage link generated inside DM controls\nRemote Jessica requires public HTTPS hosting.\n')
 web.run_app(app,host='0.0.0.0',port=args.port,print=None)
if __name__=='__main__':main()
