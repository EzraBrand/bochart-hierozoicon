(function(){
  var store={get:function(k){try{return localStorage.getItem(k)}catch(e){return null}},
             set:function(k,v){try{localStorage.setItem(k,v)}catch(e){}}};
  document.querySelectorAll('[data-toggle]').forEach(function(box){
    var cls=box.getAttribute('data-toggle'), saved=store.get('bh2-'+cls);
    if(saved!==null) box.checked = saved==='1';
    var apply=function(){document.body.classList.toggle(cls, box.checked); store.set('bh2-'+cls, box.checked?'1':'0');};
    box.addEventListener('change', apply); apply();
  });
  var th=document.getElementById('theme');
  if(th){th.value=document.documentElement.getAttribute('data-theme')||'';
    th.addEventListener('change',function(){
      if(th.value) document.documentElement.setAttribute('data-theme',th.value);
      else document.documentElement.removeAttribute('data-theme');
      store.set('bh-theme',th.value);});}
  var f=document.getElementById('filter');
  if(f){f.addEventListener('input',function(){var q=f.value.toLowerCase();
    document.querySelectorAll('table.abbr tbody tr').forEach(function(tr){
      tr.style.display = tr.textContent.toLowerCase().indexOf(q)>=0 ? '' : 'none';});});}
  // reading position: current § and page in the sticky bar, progress, contents highlight, back to top
  var bar=document.querySelector('nav.where'), top=document.querySelector('a.totop');
  var secs=[].slice.call(document.querySelectorAll('.row[id^="s"],.row[id^="l"]'));
  var pgs=[].slice.call(document.querySelectorAll('.cell.en a.pg'));
  var toc=document.getElementById('toc'), links={};
  if(toc) toc.querySelectorAll('li a').forEach(function(a){links[a.getAttribute('href').slice(1)]=a;});
  var idx=-2, ticking=false;
  function lastAbove(els,y){var i=-1;for(var k=0;k<els.length;k++){if(els[k].getBoundingClientRect().top<=y)i=k;else break;}return i;}
  function go(i){if(i>=0&&i<secs.length) location.hash='#'+secs[i].id;}
  function update(){
    ticking=false;
    if(top) top.classList.toggle('show', window.scrollY>600);
    if(!bar) return;
    var y=bar.getBoundingClientRect().bottom+12, i=lastAbove(secs,y), p=lastAbove(pgs,y);
    var h=document.documentElement;
    bar.querySelector('.prog span').style.width=(100*h.scrollTop/Math.max(1,h.scrollHeight-h.clientHeight))+'%';
    if(i!==idx){
      if(idx>=0&&links[secs[idx].id]) links[secs[idx].id].classList.remove('here');
      if(i>=0&&links[secs[i].id]) links[secs[i].id].classList.add('here');
      idx=i;
      bar.querySelector('.prev').disabled=i<=0;
      bar.querySelector('.next').disabled=i>=secs.length-1;
    }
    var a=i>=0?links[secs[i].id]:null, cur=bar.querySelector('.cur');
    cur.innerHTML='';
    if(a){var b=document.createElement('b');b.textContent=a.querySelector('b').textContent;cur.appendChild(b);
      cur.appendChild(document.createTextNode(' '+a.textContent.replace(a.querySelector('b').textContent,'').trim()));}
    else cur.textContent='Start of page';
    if(p>=0) cur.appendChild(document.createTextNode(' · '+pgs[p].textContent));
  }
  window.addEventListener('scroll',function(){if(!ticking){ticking=true;requestAnimationFrame(update);}},{passive:true});
  if(bar){
    bar.querySelector('.prev').addEventListener('click',function(){go(idx-1);});
    bar.querySelector('.next').addEventListener('click',function(){go(idx+1);});
    bar.querySelector('.open-toc').addEventListener('click',function(){toc.open=true;toc.scrollIntoView({block:'start'});});
    toc.addEventListener('toggle',function(){var h=toc.querySelector('a.here'),ul=toc.querySelector('ul');
      if(toc.open&&h) ul.scrollTop=h.parentNode.offsetTop-ul.offsetTop-ul.clientHeight/3;});
  }
  update();
  // footnote preview: hover or focus a note number to read the note in place; on touch screens
  // the first tap shows it and a second tap (or "Go to note") jumps to the notes
  var tip=document.createElement('div'); tip.className='fntip'; tip.setAttribute('role','tooltip'); tip.hidden=true;
  document.body.appendChild(tip);
  var shownFor=null, hideT=null;
  function show(a){
    var cell=document.getElementById(a.getAttribute('href').slice(1)); if(!cell) return;
    var p=cell.querySelector('p').cloneNode(true), back=p.querySelector('a.fnback');
    if(back) back.remove();
    tip.innerHTML='<b>Note '+a.textContent+'</b> ';
    tip.appendChild(p);
    var go=document.createElement('a'); go.href=a.getAttribute('href'); go.className='fngo'; go.textContent='Go to note ↓';
    tip.appendChild(go);
    tip.hidden=false;
    var r=a.getBoundingClientRect(), w=Math.min(420, window.innerWidth-24);
    tip.style.width=w+'px';
    tip.style.left=Math.max(12, Math.min(r.left+window.scrollX-w/2, window.scrollX+window.innerWidth-w-12))+'px';
    var below=r.bottom+window.scrollY+8;
    tip.style.top=below+'px';
    if(r.bottom+tip.offsetHeight+16>window.innerHeight&&r.top>tip.offsetHeight+16) tip.style.top=(r.top+window.scrollY-tip.offsetHeight-8)+'px';
    shownFor=a;
  }
  function hide(){tip.hidden=true; shownFor=null;}
  function later(){clearTimeout(hideT); hideT=setTimeout(hide,250);}
  document.querySelectorAll('a.fn').forEach(function(a){
    a.addEventListener('mouseenter',function(){clearTimeout(hideT); show(a);});
    a.addEventListener('mouseleave',later);
    a.addEventListener('focus',function(){show(a);});
    a.addEventListener('blur',later);
    a.addEventListener('click',function(ev){
      if(matchMedia('(hover: none)').matches&&shownFor!==a){ev.preventDefault(); show(a);}});
  });
  tip.addEventListener('mouseenter',function(){clearTimeout(hideT);});
  tip.addEventListener('mouseleave',later);
  document.addEventListener('click',function(ev){if(!tip.hidden&&!tip.contains(ev.target)&&!ev.target.closest('a.fn')) hide();});
  document.addEventListener('keydown',function(ev){if(ev.key==='Escape') hide();});
  // look-up on selection (14-Nov-2026): select text in a chapter to ask Google's AI mode about it, or to
  // look a Hebrew, Greek, Arabic or Latin word up, in a narrow window beside the page
  var doc=document.querySelector('main.doc');
  if(doc){
    var ask=document.createElement('div'); ask.className='askbar'; ask.hidden=true; document.body.appendChild(ask);
    var chapter=document.title.split(' · ')[0], askWin=null;
    function links(t){
      var e=encodeURIComponent, one=t.split(' ').length===1, out=[];
      out.push(['Ask Google AI','https://www.google.com/search?udm=50&q='+e('In Samuel Bochart, Hierozoicon (1663), '+chapter+', explain: "'+t+'"')]);
      out.push(['Google','https://www.google.com/search?q='+e(t)]);
      if(/[֐-׿]/.test(t)) out.push(['Sefaria','https://www.sefaria.org/search?q='+e(t)]);
      if(/[Ͱ-Ͽἀ-῿]/.test(t)&&one) out.push(['Logeion (Greek)','https://logeion.uchicago.edu/'+e(t.replace(/[.,;:·]+$/,''))]);
      if(/[؀-ۿ]/.test(t)) out.push(['Wiktionary (Arabic)','https://en.wiktionary.org/wiki/Special:Search?search='+e(t)]);
      if(/^[A-Za-z]+$/.test(t)) out.push(['Logeion (Latin)','https://logeion.uchicago.edu/'+e(t.toLowerCase())]);
      return out;
    }
    function place(){
      var s=window.getSelection(), t=s?String(s).replace(/\s+/g,' ').trim():'';
      if(!document.body.classList.contains('show-ask')||!t||t.length>400||s.rangeCount===0||!doc.contains(s.anchorNode)){ask.hidden=true;return;}
      var r=s.getRangeAt(0).getBoundingClientRect();
      ask.innerHTML='';
      links(t).forEach(function(l){var a=document.createElement('a');a.textContent=l[0];a.href=l[1];a.target='_blank';a.rel='noopener';
        a.addEventListener('click',function(ev){
          if(window.innerWidth>=900){ev.preventDefault();
            var w=Math.min(560,Math.round(screen.availWidth*0.36));
            // a new window for each look-up: Google cuts the link to a window it has loaded, and a second
            // look-up sent to the same window name then stayed on the first answer (14-Nov-2026)
            try{if(askWin&&!askWin.closed) askWin.close();}catch(e){}
            askWin=window.open(l[1],'bh-ask-'+Date.now(),'popup=yes,width='+w+',height='+screen.availHeight+',left='+(screen.availWidth-w)+',top=0');}});
        ask.appendChild(a);});
      ask.hidden=false;
      ask.style.left=Math.max(8,Math.min(r.left+window.scrollX,window.scrollX+window.innerWidth-ask.offsetWidth-8))+'px';
      ask.style.top=(r.bottom+window.scrollY+10)+'px';
    }
    var askT=null;
    document.addEventListener('selectionchange',function(){clearTimeout(askT);askT=setTimeout(place,350);});
    ask.addEventListener('mousedown',function(ev){ev.preventDefault();});
  }
})();
