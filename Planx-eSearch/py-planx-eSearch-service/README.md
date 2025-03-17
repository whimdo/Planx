nohup python main.py > logs/app.log 2>&1 &

nohup python getGroupInfo.py > logs/app.log 2>&1 &


let urls = Array.from(document.querySelectorAll('a[href*="t.me"]')).map(link => link.href).filter(url => url.includes('t.me/')).join('\n'); let temp = document.createElement('textarea'); temp.value = urls; document.body.appendChild(temp); temp.select(); document.execCommand('copy'); document.body.removeChild(temp); console.log('URLs copied to clipboard!');


kafka，milvus，mongoDB, python >= 3.10