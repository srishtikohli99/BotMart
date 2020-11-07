import numpy as np # linear algebra
import pandas as pd # data processing, CSV file I/O (e.g. pd.read_csv)
import json
import os
import en_core_web_sm
from tensorflow import keras
from sklearn.metrics import roc_curve
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split
from tensorflow.keras.utils import to_categorical
from tensorflow.keras.models import Sequential, Model
from tensorflow.keras.layers import Input, Dense, GRU, Embedding, Bidirectional, Activation
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.preprocessing.text import Tokenizer
from tensorflow.keras.preprocessing.sequence import pad_sequences
from tensorflow.keras.layers import LSTM
from tensorflow.keras.layers import SimpleRNN
from tensorflow.keras.layers import Conv1D
from tensorflow.keras.layers import Dropout
from tensorflow.keras.layers import BatchNormalization
from tensorflow.keras.layers import GlobalMaxPooling1D
from tensorflow.keras.preprocessing.text import Tokenizer, text_to_word_sequence
from tensorflow.keras.preprocessing.sequence import pad_sequences
import pickle
import re
import math
from tensorflow.keras.callbacks import ModelCheckpoint
from gensim.models import Word2Vec
import gensim

class CustomUnpickler(pickle.Unpickler):

    def find_class(self, module, name):
        try:
            return super().find_class(__name__, name)
        except AttributeError:
            return super().find_class(module, name)

class LoadingData():
            
    def __init__(self, smallTalk):
        train_file_path = os.path.join(os.getcwd(), "data")
        self.id2intent = {}
        self.intent2id = {}
        self.category_id=0
        self.entityList = set()
        print(train_file_path)
        data = {}
        for file in os.listdir(train_file_path):
            if smallTalk and str(file) == "SmallTalk":
                path = os.path.join(train_file_path, "SmallTalk")
                for fil in os.listdir(path):
                    f = open(os.path.join(path,str(fil)))
                    dat = json.load(f)
                    for key in dat:
                        data[key] = dat[key]
                        self.intent2id[key] = self.category_id
                        self.category_id+=1
            elif str(file) != "SmallTalk":
                f = open(os.path.join(train_file_path,str(file)))
                dat = json.load(f)
                for key in dat:
                    data[key] = dat[key]
                    self.intent2id[key] = self.category_id
                    self.category_id+=1
        self.data = data
        training_data=self.data_helper()
        self.train_data_frame = pd.DataFrame(training_data, columns =['query', 'intent','category']) 
        #self.train_data_frame.to_csv("out.csv",index=False)  
        for key in self.intent2id:
            self.id2intent[self.intent2id[key]]=key
        self.train_data_frame = self.train_data_frame.sample(frac = 1)

    def data_helper(self):
        sent_list = list()
        for key in self.data:
            json_dict = self.data[key]
            for i in json_dict:
                each_list = i['data']
                sent =""
                for i in each_list:
                    if 'entity' in i.keys():
                        entity = "entity" + i["entity"].replace(" ","").replace("_","")
                        sent += entity + " "
                        self.entityList.add(entity)
                    else:
                        sent = sent + i['text']+ " "
                sent =sent[:-1]
                for i in range(3):
                    sent = sent.replace("   "," ")
                    sent = sent.replace("  "," ")
                sent_list.append((sent,key,self.intent2id[key]))
        return sent_list


class Preprocessing():
    def __init__(self, maxLength):
        self.x_train = None
        self.y_train = None
        self.x_valid = None
        self.y_valid = None
        self.max_len = maxLength
        self.spacy_model = en_core_web_sm.load()
        self.tokenizer = None

    def createData(self, data, maxLength, embedding):
        sizes = []
        self.tokenizer = Tokenizer(num_words=None)
        self.max_len = maxLength
        self.x_train, self.x_valid, self.y_train, self.y_valid = train_test_split(data.train_data_frame['query'].tolist(),data.train_data_frame['category'].tolist(),test_size=0.1)
        self.tokenizer.fit_on_texts(list(self.x_train) + list(self.x_valid))
        #self.x_train = self.tokenizer.
        # index = len(self.tokenizer.word_index) + 1
        # for entity in data.entityList:
        #     self.tokenizer.word_index[entity] = index
        #     index+=1
        # print(type(self.x_train))
        # print(self.x_train[0])
        if embedding != "custom":
            for i in range(len(self.x_train)):
                self.x_train[i] = text_to_word_sequence(self.x_train[i])
                if i==0:
                    print(type(self.x_train[i]))
                sizes.append(len(self.x_train[i]))
            sizes = np.array(sizes)
            if maxLength == 0:
                
                self.max_len = math.ceil(np.mean(sizes) + 2*(np.std(sizes)))
            self.y_train = to_categorical(self.y_train)
            print("printing")
            # print(sizes)
            # print(np.mean(sizes))
            # print(np.std(sizes))
            # print(self.x_train)
        if embedding == "custom":
            self.x_train = self.tokenizer.texts_to_sequences(self.x_train)
            self.x_valid = self.tokenizer.texts_to_sequences(self.x_valid)
            if maxLength == 0:
                for i in range(len(self.x_train)):
                    sizes.append(len(self.x_train[i]))
                sizes = np.array(sizes)
                self.max_len = math.ceil(np.mean(sizes) + 2*(np.std(sizes)))
            print("printing")
            print(self.x_train[0])
            self.x_train = pad_sequences(self.x_train, maxlen=self.max_len)
            self.x_valid = pad_sequences(self.x_valid, maxlen=self.max_len)
            self.y_train = to_categorical(self.y_train)
            self.y_valid = to_categorical(self.y_valid)
        self.word_index = self.tokenizer.word_index
        with open(os.path.join(os.getcwd(), 'lstmIntent/models/maxlength.pkl'), "wb") as f:
                pickle.dump(self.max_len,f)
        print(self.max_len)
        # print("-----------------------------------------------------------------------------------")
        # print(self.word_index)

    def getSpacyEmbeddings(self,sentneces):
        sentences_vectors = list()
        for item in sentneces:
            query_vec = self.spacy_model(item) 
            sentences_vectors.append(query_vec.vector)
        return sentences_vectors
    


class DesignModel():
    def __init__(self,preprocess_obj):
        self.model = None
        self.x_train = preprocess_obj.x_train
        self.y_train = preprocess_obj.y_train
        self.x_valid = preprocess_obj.x_valid
        self.y_valid = preprocess_obj.y_valid

    def Word2VecEmbed(self, preprocess_obj):
        
        print("here1")
        Word2VecModel = Word2Vec(self.x_train,size=10*math.floor(math.log(len(preprocess_obj.word_index),10)),min_count=1)
        print("here2")
        # print(Word2VecModel.wv["restaurant"])
        Word2VecModel.save(os.path.join(os.getcwd(), "lstmIntent/models/Word2VecWE.model"))
        return Word2VecModel

    def simple_rnn(self,preprocess_obj,classes, embedding):
        
        self.model = Sequential()

        if embedding == "Word2Vec":
            model = self.Word2VecEmbed(preprocess_obj)
            #self.x_train.to_csv("out.csv", index=True)
            #print(self.x_train)
            # print(type(self.x_train))
            # print(type(self.x_train[0]))
            for i in range(len(self.x_train)):
                words = self.x_train[i]
                wv = []
                for w in words:
                    if w not in model.wv.vocab.keys():# is None:
                        continue
                    wvec = model.wv[w]
                    wv.append(wvec)
                self.x_train[i] = np.array(wv)
            self.x_train = np.array(self.x_train)
            self.x_train = keras.preprocessing.sequence.pad_sequences(self.x_train, maxlen=preprocess_obj.max_len, dtype='float32', padding='post', truncating='post')

        if embedding == "custom":
            self.model.add(Embedding(len(preprocess_obj.word_index) + 1,10*math.floor(math.log(len(preprocess_obj.word_index),10)),input_length=preprocess_obj.max_len))
        self.model.add(LSTM(32, dropout=0.2, recurrent_dropout=0.2, return_sequences=True))
        self.model.add(LSTM(64, dropout=0.25, recurrent_dropout=0.2, return_sequences=True))
        self.model.add(LSTM(128, dropout=0.3, recurrent_dropout=0.2))
        self.model.add(Dense(128, activation='relu'))
        self.model.add(Dense(256, activation='relu'))
        self.model.add(Dropout(0.2))
        self.model.add(Dense(512, activation='relu'))
        self.model.add(Dense(64, activation='relu'))
        self.model.add(Dense(classes, activation='softmax'))
        self.model.compile(loss='categorical_crossentropy', optimizer='adam', metrics=['accuracy'])
        
        
    def model_train(self,batch_size,num_epoch):
        filepath = os.path.join(os.getcwd(),"lstmIntent/models/weightsWE.best.hdf5")
        call_back = ModelCheckpoint(filepath, monitor='val_loss', verbose=0, save_best_only=True, save_weights_only=False, mode='auto')
        checkpoints = [call_back]
        print("Fitting to model")
        self.model.fit(self.x_train, self.y_train, batch_size=batch_size, epochs=num_epoch, validation_split=0.1, callbacks=checkpoints)
        print("Model Training complete.")
        self.model.save(os.path.join(os.getcwd(),"lstmIntent/models/IntentWithEntity"+".h5"))




class Prediction():
    def __init__(self):
        # with open(os.path.join(os.getcwd(), 'lstmIntent/models/WEpreprocess_obj.pkl'), "rb") as f1:
        #     preprocess_obj = pickle.load(f1)
        preprocess_obj = CustomUnpickler(open(os.path.join(os.getcwd(), 'lstmIntent/models/WEpreprocess_obj.pkl'), 'rb')).load()
        model= keras.models.load_model(os.path.join(os.getcwd(), 'lstmIntent/models/IntentWithEntity.h5'))
        self.model = model
        self.tokenizer = preprocess_obj.tokenizer
        self.max_len = preprocess_obj.max_len

    def Word2VecPredict(self, query):

        model = gensim.models.Word2Vec.load(os.path.join(os.getcwd(), 'lstmIntent/models/Word2VecWE.model'))
        query = text_to_word_sequence(query)
        
        wv=[]
        for w in query:
            if w not in model.wv.vocab.keys():# is None:
                continue
            wvec = model.wv[w]
            wv.append(wvec)
        query = np.array(wv)
        query = keras.preprocessing.sequence.pad_sequences([query], maxlen=preprocess_obj.max_len, dtype='float32', padding='post', truncating='post')
        return query

        
    
    def predict(self,query, embedding):

        with open(os.path.join(os.getcwd(), 'lstmIntent/models/WEid2intent.pkl'), "rb") as f3:
                id2intent = pickle.load(f3)
        if embedding!="custom":
            query = self.Word2VecPredict(query)
            # print(query)
            pred = self.model.predict(query)

        else:
            
            query_seq = self.tokenizer.texts_to_sequences([query])
            query_pad = pad_sequences(query_seq, maxlen=self.max_len)
            pred = self.model.predict(query_pad)
        predi = np.argmax(pred)
        # print("--------------------------")
        # print(pred)
        # print(pred[0][predi])
        # if  pred[0][predi]<0.5:
        #     return "Sorry, I don't understand!!"
        resulti = {}
        result = id2intent[predi]
        for i in range(len(pred[0])):
            resulti[id2intent[i]] = pred[0][i]
        return resulti, result

if __name__ == '__main__':

    with open(os.path.join(os.getcwd(),"config.json")) as f:
        config = json.load(f)
    epochs = 20
    batchSize = 64
    maxLength = 0
    smallTalk = False
    embedding = "custom"
    if "epochs" in config.keys():
        epochs = config["epochs"]
    if "batchSize" in config.keys():
        batchSize = config["batchSize"]
    if "maxLength" in config.keys():
        maxLength = config["maxLength"]
    if "smallTalk" in config.keys():
        smallTalk = config["smallTalk"]
    if "embedding" in config.keys():
        embedding = config["embedding"]
    data = LoadingData(smallTalk)
    preprocess_obj = Preprocessing(maxLength)
    preprocess_obj.createData(data, maxLength,embedding)
    model_obj = DesignModel(preprocess_obj)
    model_obj.simple_rnn(preprocess_obj,data.category_id, embedding)
    # print(model_obj.x_train)
    # print(type(model_obj.x_train))

    model_obj.model_train(batchSize,epochs)

    with open(os.path.join(os.getcwd(),"lstmIntent/models/WEpreprocess_obj.pkl"),"wb") as f:
        pickle.dump(preprocess_obj,f)

    with open(os.path.join(os.getcwd(),"lstmIntent/models/WEid2intent.pkl"),"wb") as f3:
        pickle.dump(data.id2intent,f3)

