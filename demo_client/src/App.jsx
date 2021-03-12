import logo from './logo.svg';
import styled from 'styled-components';
import React, { useState } from 'react';
import {dummyRows} from './dummyData';
import Rows from './Rows';
import Select from './Select';
import Insert from './Insert';
import Update from './Update';
import Delete from './Delete';

const axios = require('axios');

const SELECT = 'SELECT';
const INSERT = 'INSERT';
const UPDATE = 'UPDATE';
const DELETE = 'DELETE';

function App() {
  let [rows,setRows] = useState([]);
  let [TX, setTX] = useState([]);
  let [mode,setMode] = useState(INSERT);

  let appendTX = (newTX)=>{setTX([...TX,newTX])};

  let selectedControls = <Select appendTX={appendTX} />;
  if(mode === INSERT){
    selectedControls = <Insert appendTX={appendTX} />
  }
  if(mode === UPDATE){
    selectedControls = <Update appendTX={appendTX} />
  }
  if(mode === DELETE){
    selectedControls = <Delete appendTX={appendTX} />
  }


  return (
    <AppContainer>
      <h2>Sparkle Motion DB Demo 🐄 🥛 🐮</h2>
      <Rows rows={rows}/>
      <ControlsContainer>
        <TXContainer>
        {TX.length>0?<div>
            {
              TX.map(
                (tx)=>{
                  if(tx.type=='select'){
                    return <div>{`select rows where column ${tx.key} is ${tx.value}`}</div>
                  }
                  else if(tx.type=='insert'){
                    return <div>{`insert row with columns ${tx.col1},${tx.col2},${tx.col3},${tx.col4},${tx.col5}`}</div>
                  }
                  else if(tx.type=='update'){
                    return <div>{`update row with PK ${tx.primarykey} with columns ${tx.col2||' * '},${tx.col3||' * '},${tx.col4||' * '},${tx.col5||' * '}`}</div>
                  }
                  if(tx.type=='delete'){
                    return <div>{`delete row where PK is ${tx.key}`}</div>
                  }
                }
              )
            }
          </div>:<div>no queries added to current transaction</div>}
        </TXContainer>

        <br/>
        <SubmitButton onClick={()=>{
          // TODO call API
          axios.post('http://localhost:5000/transaction',{
            queries:TX
          }).then((res)=>{

          }).catch((error)=>{
            console.log(error);
          })
          setTX([]);
        }}>
         execute transaction
        </SubmitButton>

        <ModeButton onClick={()=>{setMode(SELECT)}} mode={mode} value={SELECT}>select</ModeButton>
        <ModeButton onClick={()=>{setMode(INSERT)}} mode={mode} value={INSERT}>insert</ModeButton>
        <ModeButton onClick={()=>{setMode(UPDATE)}} mode={mode} value={UPDATE}>update</ModeButton>
        <ModeButton onClick={()=>{setMode(DELETE)}} mode={mode} value={DELETE}>delete</ModeButton>
        
        {selectedControls}
      </ControlsContainer>
    </AppContainer>
  );
}

const TXContainer = styled.div`
box-shadow:0 30px 50px -30px rgba(0,0,0,.15);
background-color:#fff;
margin-top:10px;
padding:20px;
height:50px;
overflow-y:scroll;
`;

const SubmitButton = styled.button`
display:block;
background-color:#0cce6b;
color:'white';
border:none;
border-radius:4px;
padding:5px;
font-size:15px;

transition:border-color 0.2s, color 0.2s, background-color 0.2s;

:hover{
  background-color:#dbdbdb;
  color:black;
  border-color:#dbdbdb;
}
`;

const ModeButton = styled.button`
background-color:${props=>props.mode===props.value?'black':'white'};
color:${props=>props.mode===props.value?'white':'black'};
margin:10px 10px 10px 0px;
border:1px solid;
border-color:${props=>props.mode===props.value?'black':'#dbdbdb'};
border-radius:4px;
padding:5px;
font-size:15px;

transition:border-color 0.2s, color 0.2s, background-color 0.2s;

:hover{
  background-color:#dbdbdb;
  color:black;
  border-color:#dbdbdb;
}
`;

const AppContainer = styled.div`
  margin:auto;
  max-width:500px;
  padding:5vw;
  padding-top:15px;

`;

const ControlsContainer = styled.div`

`;

export default App;
