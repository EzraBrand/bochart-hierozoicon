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
  // text size (15-Nov-2026, issue 1): four steps, kept in the browser like the theme
  var sizes=[].slice.call(document.querySelectorAll('.size button'));
  function markSize(){var z=document.documentElement.getAttribute('data-size')||'';
    sizes.forEach(function(b){b.setAttribute('aria-pressed',String(b.getAttribute('data-size')===z));});}
  sizes.forEach(function(b){b.addEventListener('click',function(){var z=b.getAttribute('data-size');
    if(z) document.documentElement.setAttribute('data-size',z); else document.documentElement.removeAttribute('data-size');
    store.set('bh-size',z); markSize(); update();});});
  markSize();
  // paragraph tools (15-Nov-2026, issue 1), after the ¶ of each paragraph: "scan" shows the lines of the
  // paragraph on the scan (a crop from the library's image server; the place comes from data-scan, written by
  // build_site.scan_boxes), "correct" opens a GitHub issue with the paragraph link and the selected words
  var mainDoc=document.querySelector('main.doc[data-repo]');
  if(mainDoc){
    var repo=mainDoc.getAttribute('data-repo'), iiif=mainDoc.getAttribute('data-iiif'), view=mainDoc.getAttribute('data-view');
    var chap=document.title.split(' · ')[0];
    document.querySelectorAll('.row[id^="p"]').forEach(function(row){
      var host=row.querySelector('.cell.en a.anchor'), scan=row.getAttribute('data-scan'); if(!host) return;
      var fix=document.createElement('a'); fix.className='ptool fix'; fix.textContent='correct'; fix.target='_blank'; fix.rel='noopener';
      fix.title='Suggest a correction to this paragraph (opens a GitHub issue)';
      function href(){
        var s=window.getSelection(), t=s&&s.rangeCount&&row.contains(s.anchorNode)?String(s).replace(/\s+/g,' ').trim().slice(0,300):'';
        var body='Paragraph: '+location.origin+location.pathname+'#'+row.id+'\n'+(t?'Words: "'+t+'"\n':'')+'\nWhat is wrong:\n\nWhat it should be:\n';
        fix.href=repo+'/issues/new?title='+encodeURIComponent('[correction] '+chap+', '+row.id)+'&body='+encodeURIComponent(body);
      }
      href(); fix.addEventListener('pointerdown',href); fix.addEventListener('focus',href);
      host.parentNode.insertBefore(fix,host.nextSibling);
      if(!scan) return;
      var b=document.createElement('button'); b.type='button'; b.className='ptool scanbtn'; b.textContent='scan';
      b.title='Show the lines of this paragraph on the scan'; b.setAttribute('aria-expanded','false');
      b.addEventListener('click',function(){
        var box=row.querySelector('.crop');
        if(box) box.hidden=!box.hidden;
        else{
          box=document.createElement('div'); box.className='crop';
          scan.split(' ').forEach(function(s){
            var p=s.split(':'), d=p[1].split(','), a=document.createElement('a'), im=document.createElement('img');
            a.href=view+p[0]; a.target='_blank'; a.rel='noopener'; a.title='Open the full page at the library';
            im.alt='Scan of this paragraph'; im.width=d[2]; im.height=d[3];
            im.src=iiif+('0000'+p[0]).slice(-5)+'/'+p[1]+'/full/0/default.jpg';
            a.appendChild(im); box.appendChild(a);});
          row.insertBefore(box,row.firstChild);
        }
        b.setAttribute('aria-expanded',String(!box.hidden));
      });
      host.parentNode.insertBefore(b,host.nextSibling);
    });
  }
  // look-up on selection (14-Nov-2026): select text in a chapter to ask Google's AI mode about it, or to
  // look a Hebrew, Greek, Arabic or Latin word up, in a narrow window beside the page
  var doc=document.querySelector('main.doc');
  if(doc){
    var ask=document.createElement('div'); ask.className='askbar'; ask.hidden=true; document.body.appendChild(ask);
    var chapter=document.title.split(' · ')[0], askWin=null;
    // Wiktionary card (15-Nov-2026): one selected word gets a "Wiktionary" button; the definition comes from
    // the Wiktionary REST API and shows in a card on the page. Points and vowel signs are removed, then the
    // common prefixes (Hebrew, Arabic) and enclitics (Latin), until an entry in the language of the script is
    // found. A form-of entry ("genitive singular of mus") links to its headword, which opens in the same card.
    var card=document.createElement('div'); card.className='wikt'; card.hidden=true; document.body.appendChild(card);
    var wcache={}, wseq=0;
    var WL={heb:['Hebrew','Aramaic'],ara:['Arabic'],grc:['Ancient Greek'],syr:['Classical Syriac'],lat:['Latin'],en:['English','Latin']};
    var PUNCT=/^[\s.,;:!?()\[\]"'\u00b7\u00ab\u00bb\u2018\u2019\u201c\u201d\u05c3\u060c\u061b\u061f-]+|[\s.,;:!?()\[\]"'\u00b7\u00ab\u00bb\u2018\u2019\u201c\u201d\u05c3\u060c\u061b\u061f-]+$/g;
    function script(t){
      return /[\u0590-\u05ff]/.test(t)?'heb':/[\u0700-\u074f]/.test(t)?'syr':/[\u0600-\u06ff]/.test(t)?'ara':
        /[\u0370-\u03ff\u1f00-\u1fff]/.test(t)?'grc':/^[A-Za-z\u00c0-\u017f]+$/.test(t)?'lat':'';
    }
    function forms(t,sc){
      var out=[], add=function(x){if(x&&out.indexOf(x)<0) out.push(x);};
      if(sc==='heb'){
        // the plural ending goes before a prefix letter: שפנים is שפן, not ש + פנים
        var FIN={'כ':'ך','מ':'ם','נ':'ן','פ':'ף','צ':'ץ'}, h=t.replace(/[\u0591-\u05c7]/g,''), m=h;
        var both=function(x){add(x); if(x.length>3&&/(ים|ות)$/.test(x)){var s=x.slice(0,-2), c=s.slice(-1); add(FIN[c]?s.slice(0,-1)+FIN[c]:s); add(s+'ה');}};
        both(h);
        for(var k=0;k<2;k++){if(m.length>3&&/^[והבכלמש]/.test(m)){m=m.slice(1);both(m);}}}
      else if(sc==='ara'){var a=t.replace(/[\u064b-\u065f\u0670\u0640]/g,''), b=a.replace(/^[وفبلك]?ال/,''); add(a);
        if(b.length>1) add(b);
        if(a.length>3&&/^[وفبل]/.test(a)) add(a.slice(1));}
      else if(sc==='syr') add(t.replace(/[\u0730-\u074a]/g,''));
      else if(sc==='grc'){var g=t.normalize('NFD').replace(/\u0300/g,'\u0301').normalize('NFC'); add(g); add(g.toLowerCase());}
      else{var l=t.normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/æ/g,'ae').replace(/œ/g,'oe').replace(/Æ/g,'Ae').replace(/Œ/g,'Oe'), lo=l.toLowerCase();
        add(lo); add(l);
        if(sc==='lat'){add(lo.replace(/j/g,'i')); if(lo.length>4) add(lo.replace(/(que|ve|ne)$/,''));}}
      return out;
    }
    function wfetch(w){
      if(!wcache[w]) wcache[w]=fetch('https://en.wiktionary.org/api/rest_v1/page/definition/'+encodeURIComponent(w))
        .then(function(r){if(r.status===404) return null; if(!r.ok) throw new Error('HTTP '+r.status); return r.json();});
      return wcache[w];
    }
    function el(tag,cls,text){var x=document.createElement(tag); if(cls) x.className=cls; if(text) x.textContent=text; return x;}
    // copy a definition from the API into the card as text; only i, b and the headword links are kept as elements
    function copy(n,into,ctx){
      [].forEach.call(n.childNodes,function(c){
        if(c.nodeType===3){into.appendChild(document.createTextNode(c.nodeValue));return;}
        if(c.nodeType!==1) return;
        var tag=c.tagName, href=c.getAttribute('href')||'', title=c.getAttribute('title');
        if(tag==='STYLE'||tag==='SCRIPT'||tag==='SUP') return;
        if(tag==='A'&&title&&ctx.langs.some(function(L){return href.split('#')[1]===L.replace(/ /g,'_');})){
          var a=el('a','lem',c.textContent); a.setAttribute('role','button'); a.tabIndex=0;
          a.addEventListener('click',function(ev){ev.stopPropagation(); lookup(title,ctx);});
          a.addEventListener('keydown',function(ev){if(ev.key==='Enter') lookup(title,ctx);});
          into.appendChild(a); return;}
        var box=into;
        if(tag==='LI'||tag==='DD'){box=el('div','sub'); into.appendChild(box);}
        else if(tag==='I'||tag==='B'||tag==='EM'||tag==='STRONG'){box=el(tag.toLowerCase()); into.appendChild(box);}
        copy(c,box,ctx);
      });
    }
    function frame(word,note){
      card.innerHTML='';
      var x=el('button','x','×'); x.type='button'; x.setAttribute('aria-label','Close'); x.addEventListener('click',function(){card.hidden=true;});
      var h=el('h4'), b=el('bdi','',word); h.appendChild(b); if(note) h.appendChild(el('small','',note));
      card.appendChild(x); card.appendChild(h);
    }
    function source(word,ctx,found){
      var e=encodeURIComponent, s=el('div','src'), add=function(text,url){var a=el('a','',text); a.href=url; a.target='_blank'; a.rel='noopener'; s.appendChild(a);};
      if(found) add('Full entry on Wiktionary ↗','https://en.wiktionary.org/wiki/'+e(word)+'#'+found.replace(/ /g,'_'));
      else add('Search Wiktionary ↗','https://en.wiktionary.org/wiki/Special:Search?search='+e(word));
      if(ctx.sc==='grc'||ctx.sc==='lat') add('Logeion ↗','https://logeion.uchicago.edu/'+e(word));
      if(found) s.appendChild(document.createTextNode('Text: Wiktionary, CC BY-SA 4.0'));
      card.appendChild(s);
    }
    function lookup(t,ctx){
      var seq=++wseq, cand=forms(t,ctx.sc), i=0;
      frame(t,'looking up …'); card.hidden=false;
      (function next(){
        if(i>=cand.length){frame(t); card.appendChild(el('p','','No '+ctx.langs.join(' or ')+' entry in Wiktionary for this form.')); source(cand[0]||t,ctx,''); return;}
        var w=cand[i++];
        wfetch(w).then(function(j){
          if(seq!==wseq) return;
          var secs=[];
          if(j) ctx.langs.forEach(function(L){Object.keys(j).forEach(function(k){j[k].forEach(function(s){if(s.language===L) secs.push(s);});});});
          if(!secs.length) return next();
          frame(w, w===t?'':'from '+t);
          var tmp=document.createElement('template');
          secs.forEach(function(s){
            card.appendChild(el('div','pos',s.language+' · '+s.partOfSpeech));
            var ol=el('ol'), seen=''; card.appendChild(ol);
            s.definitions.slice(0,8).forEach(function(d){
              tmp.innerHTML=d.definition||'';
              // the API gives the sub-lines of an "inflection of" entry a second time, as definitions
              var txt=tmp.content.textContent.trim();
              if(!txt||seen.indexOf(txt)>=0) return;
              seen+='\n'+txt;
              var li=el('li'); copy(tmp.content,li,ctx); ol.appendChild(li);});
          });
          source(w,ctx,secs[0].language); card.scrollTop=0;
        }).catch(function(){
          if(seq!==wseq) return;
          delete wcache[w]; frame(t); card.appendChild(el('p','','Wiktionary did not answer. Try again, or open the entry:')); source(cand[0]||t,ctx,'');
        });
      })();
    }
    document.addEventListener('click',function(ev){if(!card.hidden&&!card.contains(ev.target)&&!ask.contains(ev.target)) card.hidden=true;});
    document.addEventListener('keydown',function(ev){if(ev.key==='Escape') card.hidden=true;});
    function links(t,inEn){
      var e=encodeURIComponent, one=t.split(' ').length===1, out=[], w=t.replace(PUNCT,''), sc=one?script(w):'';
      if(sc){if(sc==='lat'&&inEn) sc='en';
        out.push(['Wiktionary','https://en.wiktionary.org/wiki/Special:Search?search='+e(w),function(){
          lookup(w,{sc:sc,langs:WL[sc]});
          card.style.left=Math.max(8,Math.min(ask.offsetLeft,window.scrollX+window.innerWidth-card.offsetWidth-8))+'px';
          card.style.top=(ask.offsetTop+ask.offsetHeight+6)+'px';}]);}
      out.push(['Ask Google AI','https://www.google.com/search?udm=50&q='+e('In Samuel Bochart, Hierozoicon (1663), '+chapter+', explain: "'+t+'"')]);
      out.push(['Google','https://www.google.com/search?q='+e(t)]);
      if(/[֐-׿]/.test(t)) out.push(['Sefaria','https://www.sefaria.org/search?q='+e(t)]);
      if(/[Ͱ-Ͽἀ-῿]/.test(t)&&one) out.push(['Logeion (Greek)','https://logeion.uchicago.edu/'+e(t.replace(/[.,;:·]+$/,''))]);
      if(/^[A-Za-z]+$/.test(t)) out.push(['Logeion (Latin)','https://logeion.uchicago.edu/'+e(t.toLowerCase())]);
      return out;
    }
    function place(){
      var s=window.getSelection(), t=s?String(s).replace(/\s+/g,' ').trim():'';
      if(!document.body.classList.contains('show-ask')||!t||t.length>400||s.rangeCount===0||!doc.contains(s.anchorNode)){ask.hidden=true;return;}
      var r=s.getRangeAt(0).getBoundingClientRect();
      ask.innerHTML='';
      var an=s.anchorNode.nodeType===1?s.anchorNode:s.anchorNode.parentElement;
      links(t,!!(an&&an.closest('.cell.en'))).forEach(function(l){var a=document.createElement('a');a.textContent=l[0];a.href=l[1];a.target='_blank';a.rel='noopener';
        a.addEventListener('click',function(ev){
          if(l[2]){ev.preventDefault(); l[2](); return;}
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
