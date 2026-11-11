// 获取基底 substrate 透过率数组 [wl, trans]
async function getSubstrateTransmission() {
    try {
        const fileInput = document.getElementById('substrateTransFile');
        if (fileInput && fileInput.files.length > 0) {
            const data = await parseTransmissionUploadFile(fileInput.files[0]);
            data.sort((a,b) => a[0] - b[0]);
            return data;
        }
        const presetSelect = document.getElementById('substrateTransPresets');
        if (presetSelect && presetSelect.value) {
            const key = presetSelect.value;
            if (typeof transPresets !== 'undefined' && transPresets[key]) {
                return parseTransPresetToTrans(transPresets[key]);
            }
            if (typeof eqePresets !== 'undefined' && eqePresets[key]) {
                const preset = JSON.parse(JSON.stringify(eqePresets[key]));
                preset.sort((a,b)=>a[0]-b[0]);
                return preset.map(r=>[r[0], Math.max(0, Math.min(1, 1 - parseFloat(r[1] || 0)))]);
            }
        }
        return [];
    } catch (err) {
        console.error('getSubstrateTransmission error', err);
        return [];
    }
}

// 获取顶电极 top electrode 透过率数组 [wl, trans]
async function getTopElectrodeTransmission() {
    try {
        const fileInput = document.getElementById('topElectrodeTransFile');
        if (fileInput && fileInput.files.length > 0) {
            const data = await parseTransmissionUploadFile(fileInput.files[0]);
            data.sort((a,b) => a[0] - b[0]);
            return data;
        }
        const presetSelect = document.getElementById('topElectrodeTransPresets');
        if (presetSelect && presetSelect.value) {
            const key = presetSelect.value;
            if (typeof transPresets !== 'undefined' && transPresets[key]) {
                return parseTransPresetToTrans(transPresets[key]);
            }
            if (typeof eqePresets !== 'undefined' && eqePresets[key]) {
                const preset = JSON.parse(JSON.stringify(eqePresets[key]));
                preset.sort((a,b)=>a[0]-b[0]);
                return preset.map(r=>[r[0], Math.max(0, Math.min(1, 1 - parseFloat(r[1] || 0)))]);
            }
        }
        return [];
    } catch (err) {
        console.error('getTopElectrodeTransmission error', err);
        return [];
    }
}
