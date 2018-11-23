#!/bin/bash

while read mid; do
curl "https://academic.microsoft.com/api/browse/GetEntityDetails?entityId=${mid}&correlationId=3c0aefbf-942a-42b1-bac1-351c6b024682" -H 'Cookie: brwsr=8d4611b9-299b-6ebe-f7fe-42be1c0d954e; msacademic=59937d3e-a0ff-4b9a-8942-49c6f98c4b36; ai_user=L3Ib/|2018-11-22T17:50:56.269Z; MSCC=1542909112; MUID=27D0D5B746246DC5263FD90740246D14; MS0=54DC08ED36064F7AB5DB943227AF1086; ak_bmsc=6E3C828DE1A236B117FFCCCA6F1E2E580214844B880300009BE0F75BA48C2173~pl7H1UOzkMaLUKllrdizeOVyiErmQlkIO2u3VyRLiH/VQhB7sTFUTATNOj0ACzMo12IXv5LrOZ8quTF5lLh+NHxnOcKYF9qffX1WlvquR6cld+7nArB6FGwQGWYKXa7nw2O1tSGyogNw0v9b2aiSTMRx0rhA+DVAs5XHMIQPm4WGPFPCCJkJZVzaAnN6Lj7ILMifpmpkV4y5Iy9YD3QFE7xopiFTHmfa7paWBrNzkD8Ng=; bm_sv=EDEC7DEF82425634A06A63D12D7EA4AB~nBMOhhPqALVWxghn2ZtF/c4Cbf5cVIc01V/ePQTHaFispVYJ+UDiTD++xaDSWHYAAAV7GvKgGlpONwRVrd0foJKf7FmE5zut1TKp/NmoxidnlEMhQKy4ALv/KuHcunkZqNwYbMVUCpxMkgBLXzFjYW3I/6XwjtgJg7g1YQsxRZ4=; ARRAffinity=e6f24eb4d319e773b8a35736f11b30eacde896adab586211f1dfa88ef0624c3c' -H 'Accept-Encoding: gzip, deflate, br' -H 'Accept-Language: en-US,en;q=0.9' -H 'User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Ubuntu Chromium/69.0.3497.81 Chrome/69.0.3497.81 Safari/537.36' -H 'v: 204140489' -H 'Accept: */*' -H 'Referer: https://academic.microsoft.com/' -H 'X-Requested-With: XMLHttpRequest' -H 'Connection: keep-alive' --compressed > out.json
python3 -c 'import json;f = open("out.json");j=json.load(f);f.close();fos=" ".join([str(x["id"]) for x in j["fieldsOfStudy"]]);print(fos)' > "${mid}.out"
rm out.json
sleep 0.05
done <mids
