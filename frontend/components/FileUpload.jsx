import { useCallback } from 'react';
import { useDropzone } from 'react-dropzone';

export default function FileUpload({ onUpload }) {
  const onDrop = useCallback((files) => {
    if (files.length > 0) onUpload(files[0]);
  }, [onUpload]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/vnd.ms-excel': ['.xls'],
      'text/csv': ['.csv'],
    },
    maxFiles: 1,
    multiple: false,
  });

  return (
    <div
      {...getRootProps()}
      className={`upload-zone ${isDragActive ? 'active' : ''}`}
    >
      <input {...getInputProps()} />
      <div className="upload-zone-icon">{isDragActive ? '📂' : '📄'}</div>
      <div className="upload-zone-title">
        {isDragActive ? 'Отпустите для загрузки' : 'Загрузите Excel-файл'}
      </div>
      <div className="upload-zone-subtitle">
        Перетащите файл или нажмите для выбора
      </div>
      <div className="upload-formats">
        <span className="format-badge">.xlsx</span>
        <span className="format-badge">.xls</span>
        <span className="format-badge">.csv</span>
      </div>
    </div>
  );
}
