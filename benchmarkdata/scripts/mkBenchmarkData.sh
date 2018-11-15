#!/bin/bash

for i in {1..6} 8; do if [ ! -e "../f${i}.txt" ];                then python mkBenchmarkData.py -c -o ../f${i}.txt                        -n 1000   -r 0   -f ${i}; fi done
for i in {1..6} 8; do if [ ! -e "../f${i}_noise_0.1.txt" ];      then python mkBenchmarkData.py -c -o ../f${i}_noise_0.1.txt              -n 1000   -r 0.1 -f ${i}; fi done
for i in {1..6} 8; do if [ ! -e "../f${i}_noise_0.5.txt" ];      then python mkBenchmarkData.py -c -o ../f${i}_noise_0.5.txt              -n 1000   -r 0.5 -f ${i}; fi done
for i in {1..6} 8; do if [ ! -e "../f${i}_test.txt" ];           then python mkBenchmarkData.py -c -o ../f${i}_test.txt           -s 9999 -n 100000 -r 0   -f ${i}; fi done
for i in {1..6} 8; do if [ ! -e "../f${i}_noise_0.1_test.txt" ]; then python mkBenchmarkData.py -c -o ../f${i}_noise_0.1_test.txt -s 9999 -n 100000 -r 0.1 -f ${i}; fi done
for i in {1..6} 8; do if [ ! -e "../f${i}_noise_0.5_test.txt" ]; then python mkBenchmarkData.py -c -o ../f${i}_noise_0.5_test.txt -s 9999 -n 100000 -r 0.5 -f ${i}; fi done

for i in 7; do if [ ! -e "../f${i}.txt" ];                then python mkBenchmarkData.py -o ../f${i}.txt                        -n 1000   -r 0   -f ${i} --xmin 0 --xmax 1; fi done
for i in 7; do if [ ! -e "../f${i}_noise_0.1.txt" ];      then python mkBenchmarkData.py -o ../f${i}_noise_0.1.txt              -n 1000   -r 0.1 -f ${i} --xmin 0 --xmax 1; fi done
for i in 7; do if [ ! -e "../f${i}_noise_0.5.txt" ];      then python mkBenchmarkData.py -o ../f${i}_noise_0.5.txt              -n 1000   -r 0.5 -f ${i} --xmin 0 --xmax 1; fi done
for i in 7; do if [ ! -e "../f${i}_test.txt" ];           then python mkBenchmarkData.py -o ../f${i}_test.txt           -s 9999 -n 100000 -r 0   -f ${i} --xmin 0 --xmax 1; fi done
for i in 7; do if [ ! -e "../f${i}_noise_0.1_test.txt" ]; then python mkBenchmarkData.py -o ../f${i}_noise_0.1_test.txt -s 9999 -n 100000 -r 0.1 -f ${i} --xmin 0 --xmax 1; fi done
for i in 7; do if [ ! -e "../f${i}_noise_0.5_test.txt" ]; then python mkBenchmarkData.py -o ../f${i}_noise_0.5_test.txt -s 9999 -n 100000 -r 0.5 -f ${i} --xmin 0 --xmax 1; fi done