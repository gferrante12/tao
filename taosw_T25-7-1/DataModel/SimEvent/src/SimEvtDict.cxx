// Do NOT change. Changes will be lost next time file is generated

#define R__DICTIONARY_FILENAME dItmpdIbdIjunodOihepdOacdOcndIel9_amd64_gcc11dIReleasedIJ25dO7dO1dItaoswdIbuilddIDataModeldISimEventdIsrcdISimEvtDict
#define R__NO_DEPRECATION

/*******************************************************************/
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>
#define G__DICTIONARY
#include "ROOT/RConfig.hxx"
#include "TClass.h"
#include "TDictAttributeMap.h"
#include "TInterpreter.h"
#include "TROOT.h"
#include "TBuffer.h"
#include "TMemberInspector.h"
#include "TInterpreter.h"
#include "TVirtualMutex.h"
#include "TError.h"

#ifndef G__ROOT
#define G__ROOT
#endif

#include "RtypesImp.h"
#include "TIsAProxy.h"
#include "TFileMergeInfo.h"
#include <algorithm>
#include "TCollectionProxyInfo.h"
/*******************************************************************/

#include "TDataMember.h"

// Header files passed as explicit arguments
#include "/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/DataModel/SimEvent/Event/SimEvt.h"

// Header files passed via #pragma extra_include

// The generated code does not explicitly qualify STL entities
namespace std {} using namespace std;

namespace ROOT {
   static void *new_TaocLcLSimEvt(void *p = nullptr);
   static void *newArray_TaocLcLSimEvt(Long_t size, void *p);
   static void delete_TaocLcLSimEvt(void *p);
   static void deleteArray_TaocLcLSimEvt(void *p);
   static void destruct_TaocLcLSimEvt(void *p);

   // Function generating the singleton type initializer
   static TGenericClassInfo *GenerateInitInstanceLocal(const ::Tao::SimEvt*)
   {
      ::Tao::SimEvt *ptr = nullptr;
      static ::TVirtualIsAProxy* isa_proxy = new ::TInstrumentedIsAProxy< ::Tao::SimEvt >(nullptr);
      static ::ROOT::TGenericClassInfo 
         instance("Tao::SimEvt", ::Tao::SimEvt::Class_Version(), "Event/SimEvt.h", 17,
                  typeid(::Tao::SimEvt), ::ROOT::Internal::DefineBehavior(ptr, ptr),
                  &::Tao::SimEvt::Dictionary, isa_proxy, 4,
                  sizeof(::Tao::SimEvt) );
      instance.SetNew(&new_TaocLcLSimEvt);
      instance.SetNewArray(&newArray_TaocLcLSimEvt);
      instance.SetDelete(&delete_TaocLcLSimEvt);
      instance.SetDeleteArray(&deleteArray_TaocLcLSimEvt);
      instance.SetDestructor(&destruct_TaocLcLSimEvt);
      return &instance;
   }
   TGenericClassInfo *GenerateInitInstance(const ::Tao::SimEvt*)
   {
      return GenerateInitInstanceLocal(static_cast<::Tao::SimEvt*>(nullptr));
   }
   // Static variable to force the class initialization
   static ::ROOT::TGenericClassInfo *_R__UNIQUE_DICT_(Init) = GenerateInitInstanceLocal(static_cast<const ::Tao::SimEvt*>(nullptr)); R__UseDummy(_R__UNIQUE_DICT_(Init));
} // end of namespace ROOT

namespace Tao {
//______________________________________________________________________________
atomic_TClass_ptr SimEvt::fgIsA(nullptr);  // static to hold class pointer

//______________________________________________________________________________
const char *SimEvt::Class_Name()
{
   return "Tao::SimEvt";
}

//______________________________________________________________________________
const char *SimEvt::ImplFileName()
{
   return ::ROOT::GenerateInitInstanceLocal((const ::Tao::SimEvt*)nullptr)->GetImplFileName();
}

//______________________________________________________________________________
int SimEvt::ImplFileLine()
{
   return ::ROOT::GenerateInitInstanceLocal((const ::Tao::SimEvt*)nullptr)->GetImplFileLine();
}

//______________________________________________________________________________
TClass *SimEvt::Dictionary()
{
   fgIsA = ::ROOT::GenerateInitInstanceLocal((const ::Tao::SimEvt*)nullptr)->GetClass();
   return fgIsA;
}

//______________________________________________________________________________
TClass *SimEvt::Class()
{
   if (!fgIsA.load()) { R__LOCKGUARD(gInterpreterMutex); fgIsA = ::ROOT::GenerateInitInstanceLocal((const ::Tao::SimEvt*)nullptr)->GetClass(); }
   return fgIsA;
}

} // namespace Tao
namespace Tao {
//______________________________________________________________________________
void SimEvt::Streamer(TBuffer &R__b)
{
   // Stream an object of class Tao::SimEvt.

   if (R__b.IsReading()) {
      R__b.ReadClassBuffer(Tao::SimEvt::Class(),this);
   } else {
      R__b.WriteClassBuffer(Tao::SimEvt::Class(),this);
   }
}

} // namespace Tao
namespace ROOT {
   // Wrappers around operator new
   static void *new_TaocLcLSimEvt(void *p) {
      return  p ? new(p) ::Tao::SimEvt : new ::Tao::SimEvt;
   }
   static void *newArray_TaocLcLSimEvt(Long_t nElements, void *p) {
      return p ? new(p) ::Tao::SimEvt[nElements] : new ::Tao::SimEvt[nElements];
   }
   // Wrapper around operator delete
   static void delete_TaocLcLSimEvt(void *p) {
      delete (static_cast<::Tao::SimEvt*>(p));
   }
   static void deleteArray_TaocLcLSimEvt(void *p) {
      delete [] (static_cast<::Tao::SimEvt*>(p));
   }
   static void destruct_TaocLcLSimEvt(void *p) {
      typedef ::Tao::SimEvt current_t;
      (static_cast<current_t*>(p))->~current_t();
   }
} // end of namespace ROOT for class ::Tao::SimEvt

namespace ROOT {
   static TClass *vectorlETaocLcLSimTrackmUgR_Dictionary();
   static void vectorlETaocLcLSimTrackmUgR_TClassManip(TClass*);
   static void *new_vectorlETaocLcLSimTrackmUgR(void *p = nullptr);
   static void *newArray_vectorlETaocLcLSimTrackmUgR(Long_t size, void *p);
   static void delete_vectorlETaocLcLSimTrackmUgR(void *p);
   static void deleteArray_vectorlETaocLcLSimTrackmUgR(void *p);
   static void destruct_vectorlETaocLcLSimTrackmUgR(void *p);

   // Function generating the singleton type initializer
   static TGenericClassInfo *GenerateInitInstanceLocal(const vector<Tao::SimTrack*>*)
   {
      vector<Tao::SimTrack*> *ptr = nullptr;
      static ::TVirtualIsAProxy* isa_proxy = new ::TIsAProxy(typeid(vector<Tao::SimTrack*>));
      static ::ROOT::TGenericClassInfo 
         instance("vector<Tao::SimTrack*>", -2, "vector", 389,
                  typeid(vector<Tao::SimTrack*>), ::ROOT::Internal::DefineBehavior(ptr, ptr),
                  &vectorlETaocLcLSimTrackmUgR_Dictionary, isa_proxy, 0,
                  sizeof(vector<Tao::SimTrack*>) );
      instance.SetNew(&new_vectorlETaocLcLSimTrackmUgR);
      instance.SetNewArray(&newArray_vectorlETaocLcLSimTrackmUgR);
      instance.SetDelete(&delete_vectorlETaocLcLSimTrackmUgR);
      instance.SetDeleteArray(&deleteArray_vectorlETaocLcLSimTrackmUgR);
      instance.SetDestructor(&destruct_vectorlETaocLcLSimTrackmUgR);
      instance.AdoptCollectionProxyInfo(TCollectionProxyInfo::Generate(TCollectionProxyInfo::Pushback< vector<Tao::SimTrack*> >()));

      instance.AdoptAlternate(::ROOT::AddClassAlternate("vector<Tao::SimTrack*>","std::vector<Tao::SimTrack*, std::allocator<Tao::SimTrack*> >"));
      return &instance;
   }
   // Static variable to force the class initialization
   static ::ROOT::TGenericClassInfo *_R__UNIQUE_DICT_(Init) = GenerateInitInstanceLocal(static_cast<const vector<Tao::SimTrack*>*>(nullptr)); R__UseDummy(_R__UNIQUE_DICT_(Init));

   // Dictionary for non-ClassDef classes
   static TClass *vectorlETaocLcLSimTrackmUgR_Dictionary() {
      TClass* theClass =::ROOT::GenerateInitInstanceLocal(static_cast<const vector<Tao::SimTrack*>*>(nullptr))->GetClass();
      vectorlETaocLcLSimTrackmUgR_TClassManip(theClass);
   return theClass;
   }

   static void vectorlETaocLcLSimTrackmUgR_TClassManip(TClass* ){
   }

} // end of namespace ROOT

namespace ROOT {
   // Wrappers around operator new
   static void *new_vectorlETaocLcLSimTrackmUgR(void *p) {
      return  p ? ::new(static_cast<::ROOT::Internal::TOperatorNewHelper*>(p)) vector<Tao::SimTrack*> : new vector<Tao::SimTrack*>;
   }
   static void *newArray_vectorlETaocLcLSimTrackmUgR(Long_t nElements, void *p) {
      return p ? ::new(static_cast<::ROOT::Internal::TOperatorNewHelper*>(p)) vector<Tao::SimTrack*>[nElements] : new vector<Tao::SimTrack*>[nElements];
   }
   // Wrapper around operator delete
   static void delete_vectorlETaocLcLSimTrackmUgR(void *p) {
      delete (static_cast<vector<Tao::SimTrack*>*>(p));
   }
   static void deleteArray_vectorlETaocLcLSimTrackmUgR(void *p) {
      delete [] (static_cast<vector<Tao::SimTrack*>*>(p));
   }
   static void destruct_vectorlETaocLcLSimTrackmUgR(void *p) {
      typedef vector<Tao::SimTrack*> current_t;
      (static_cast<current_t*>(p))->~current_t();
   }
} // end of namespace ROOT for class vector<Tao::SimTrack*>

namespace ROOT {
   static TClass *vectorlETaocLcLSimTVTHitmUgR_Dictionary();
   static void vectorlETaocLcLSimTVTHitmUgR_TClassManip(TClass*);
   static void *new_vectorlETaocLcLSimTVTHitmUgR(void *p = nullptr);
   static void *newArray_vectorlETaocLcLSimTVTHitmUgR(Long_t size, void *p);
   static void delete_vectorlETaocLcLSimTVTHitmUgR(void *p);
   static void deleteArray_vectorlETaocLcLSimTVTHitmUgR(void *p);
   static void destruct_vectorlETaocLcLSimTVTHitmUgR(void *p);

   // Function generating the singleton type initializer
   static TGenericClassInfo *GenerateInitInstanceLocal(const vector<Tao::SimTVTHit*>*)
   {
      vector<Tao::SimTVTHit*> *ptr = nullptr;
      static ::TVirtualIsAProxy* isa_proxy = new ::TIsAProxy(typeid(vector<Tao::SimTVTHit*>));
      static ::ROOT::TGenericClassInfo 
         instance("vector<Tao::SimTVTHit*>", -2, "vector", 389,
                  typeid(vector<Tao::SimTVTHit*>), ::ROOT::Internal::DefineBehavior(ptr, ptr),
                  &vectorlETaocLcLSimTVTHitmUgR_Dictionary, isa_proxy, 0,
                  sizeof(vector<Tao::SimTVTHit*>) );
      instance.SetNew(&new_vectorlETaocLcLSimTVTHitmUgR);
      instance.SetNewArray(&newArray_vectorlETaocLcLSimTVTHitmUgR);
      instance.SetDelete(&delete_vectorlETaocLcLSimTVTHitmUgR);
      instance.SetDeleteArray(&deleteArray_vectorlETaocLcLSimTVTHitmUgR);
      instance.SetDestructor(&destruct_vectorlETaocLcLSimTVTHitmUgR);
      instance.AdoptCollectionProxyInfo(TCollectionProxyInfo::Generate(TCollectionProxyInfo::Pushback< vector<Tao::SimTVTHit*> >()));

      instance.AdoptAlternate(::ROOT::AddClassAlternate("vector<Tao::SimTVTHit*>","std::vector<Tao::SimTVTHit*, std::allocator<Tao::SimTVTHit*> >"));
      return &instance;
   }
   // Static variable to force the class initialization
   static ::ROOT::TGenericClassInfo *_R__UNIQUE_DICT_(Init) = GenerateInitInstanceLocal(static_cast<const vector<Tao::SimTVTHit*>*>(nullptr)); R__UseDummy(_R__UNIQUE_DICT_(Init));

   // Dictionary for non-ClassDef classes
   static TClass *vectorlETaocLcLSimTVTHitmUgR_Dictionary() {
      TClass* theClass =::ROOT::GenerateInitInstanceLocal(static_cast<const vector<Tao::SimTVTHit*>*>(nullptr))->GetClass();
      vectorlETaocLcLSimTVTHitmUgR_TClassManip(theClass);
   return theClass;
   }

   static void vectorlETaocLcLSimTVTHitmUgR_TClassManip(TClass* ){
   }

} // end of namespace ROOT

namespace ROOT {
   // Wrappers around operator new
   static void *new_vectorlETaocLcLSimTVTHitmUgR(void *p) {
      return  p ? ::new(static_cast<::ROOT::Internal::TOperatorNewHelper*>(p)) vector<Tao::SimTVTHit*> : new vector<Tao::SimTVTHit*>;
   }
   static void *newArray_vectorlETaocLcLSimTVTHitmUgR(Long_t nElements, void *p) {
      return p ? ::new(static_cast<::ROOT::Internal::TOperatorNewHelper*>(p)) vector<Tao::SimTVTHit*>[nElements] : new vector<Tao::SimTVTHit*>[nElements];
   }
   // Wrapper around operator delete
   static void delete_vectorlETaocLcLSimTVTHitmUgR(void *p) {
      delete (static_cast<vector<Tao::SimTVTHit*>*>(p));
   }
   static void deleteArray_vectorlETaocLcLSimTVTHitmUgR(void *p) {
      delete [] (static_cast<vector<Tao::SimTVTHit*>*>(p));
   }
   static void destruct_vectorlETaocLcLSimTVTHitmUgR(void *p) {
      typedef vector<Tao::SimTVTHit*> current_t;
      (static_cast<current_t*>(p))->~current_t();
   }
} // end of namespace ROOT for class vector<Tao::SimTVTHit*>

namespace ROOT {
   static TClass *vectorlETaocLcLSimSipmHitmUgR_Dictionary();
   static void vectorlETaocLcLSimSipmHitmUgR_TClassManip(TClass*);
   static void *new_vectorlETaocLcLSimSipmHitmUgR(void *p = nullptr);
   static void *newArray_vectorlETaocLcLSimSipmHitmUgR(Long_t size, void *p);
   static void delete_vectorlETaocLcLSimSipmHitmUgR(void *p);
   static void deleteArray_vectorlETaocLcLSimSipmHitmUgR(void *p);
   static void destruct_vectorlETaocLcLSimSipmHitmUgR(void *p);

   // Function generating the singleton type initializer
   static TGenericClassInfo *GenerateInitInstanceLocal(const vector<Tao::SimSipmHit*>*)
   {
      vector<Tao::SimSipmHit*> *ptr = nullptr;
      static ::TVirtualIsAProxy* isa_proxy = new ::TIsAProxy(typeid(vector<Tao::SimSipmHit*>));
      static ::ROOT::TGenericClassInfo 
         instance("vector<Tao::SimSipmHit*>", -2, "vector", 389,
                  typeid(vector<Tao::SimSipmHit*>), ::ROOT::Internal::DefineBehavior(ptr, ptr),
                  &vectorlETaocLcLSimSipmHitmUgR_Dictionary, isa_proxy, 0,
                  sizeof(vector<Tao::SimSipmHit*>) );
      instance.SetNew(&new_vectorlETaocLcLSimSipmHitmUgR);
      instance.SetNewArray(&newArray_vectorlETaocLcLSimSipmHitmUgR);
      instance.SetDelete(&delete_vectorlETaocLcLSimSipmHitmUgR);
      instance.SetDeleteArray(&deleteArray_vectorlETaocLcLSimSipmHitmUgR);
      instance.SetDestructor(&destruct_vectorlETaocLcLSimSipmHitmUgR);
      instance.AdoptCollectionProxyInfo(TCollectionProxyInfo::Generate(TCollectionProxyInfo::Pushback< vector<Tao::SimSipmHit*> >()));

      instance.AdoptAlternate(::ROOT::AddClassAlternate("vector<Tao::SimSipmHit*>","std::vector<Tao::SimSipmHit*, std::allocator<Tao::SimSipmHit*> >"));
      return &instance;
   }
   // Static variable to force the class initialization
   static ::ROOT::TGenericClassInfo *_R__UNIQUE_DICT_(Init) = GenerateInitInstanceLocal(static_cast<const vector<Tao::SimSipmHit*>*>(nullptr)); R__UseDummy(_R__UNIQUE_DICT_(Init));

   // Dictionary for non-ClassDef classes
   static TClass *vectorlETaocLcLSimSipmHitmUgR_Dictionary() {
      TClass* theClass =::ROOT::GenerateInitInstanceLocal(static_cast<const vector<Tao::SimSipmHit*>*>(nullptr))->GetClass();
      vectorlETaocLcLSimSipmHitmUgR_TClassManip(theClass);
   return theClass;
   }

   static void vectorlETaocLcLSimSipmHitmUgR_TClassManip(TClass* ){
   }

} // end of namespace ROOT

namespace ROOT {
   // Wrappers around operator new
   static void *new_vectorlETaocLcLSimSipmHitmUgR(void *p) {
      return  p ? ::new(static_cast<::ROOT::Internal::TOperatorNewHelper*>(p)) vector<Tao::SimSipmHit*> : new vector<Tao::SimSipmHit*>;
   }
   static void *newArray_vectorlETaocLcLSimSipmHitmUgR(Long_t nElements, void *p) {
      return p ? ::new(static_cast<::ROOT::Internal::TOperatorNewHelper*>(p)) vector<Tao::SimSipmHit*>[nElements] : new vector<Tao::SimSipmHit*>[nElements];
   }
   // Wrapper around operator delete
   static void delete_vectorlETaocLcLSimSipmHitmUgR(void *p) {
      delete (static_cast<vector<Tao::SimSipmHit*>*>(p));
   }
   static void deleteArray_vectorlETaocLcLSimSipmHitmUgR(void *p) {
      delete [] (static_cast<vector<Tao::SimSipmHit*>*>(p));
   }
   static void destruct_vectorlETaocLcLSimSipmHitmUgR(void *p) {
      typedef vector<Tao::SimSipmHit*> current_t;
      (static_cast<current_t*>(p))->~current_t();
   }
} // end of namespace ROOT for class vector<Tao::SimSipmHit*>

namespace ROOT {
   static TClass *vectorlETaocLcLSimPmtHitmUgR_Dictionary();
   static void vectorlETaocLcLSimPmtHitmUgR_TClassManip(TClass*);
   static void *new_vectorlETaocLcLSimPmtHitmUgR(void *p = nullptr);
   static void *newArray_vectorlETaocLcLSimPmtHitmUgR(Long_t size, void *p);
   static void delete_vectorlETaocLcLSimPmtHitmUgR(void *p);
   static void deleteArray_vectorlETaocLcLSimPmtHitmUgR(void *p);
   static void destruct_vectorlETaocLcLSimPmtHitmUgR(void *p);

   // Function generating the singleton type initializer
   static TGenericClassInfo *GenerateInitInstanceLocal(const vector<Tao::SimPmtHit*>*)
   {
      vector<Tao::SimPmtHit*> *ptr = nullptr;
      static ::TVirtualIsAProxy* isa_proxy = new ::TIsAProxy(typeid(vector<Tao::SimPmtHit*>));
      static ::ROOT::TGenericClassInfo 
         instance("vector<Tao::SimPmtHit*>", -2, "vector", 389,
                  typeid(vector<Tao::SimPmtHit*>), ::ROOT::Internal::DefineBehavior(ptr, ptr),
                  &vectorlETaocLcLSimPmtHitmUgR_Dictionary, isa_proxy, 0,
                  sizeof(vector<Tao::SimPmtHit*>) );
      instance.SetNew(&new_vectorlETaocLcLSimPmtHitmUgR);
      instance.SetNewArray(&newArray_vectorlETaocLcLSimPmtHitmUgR);
      instance.SetDelete(&delete_vectorlETaocLcLSimPmtHitmUgR);
      instance.SetDeleteArray(&deleteArray_vectorlETaocLcLSimPmtHitmUgR);
      instance.SetDestructor(&destruct_vectorlETaocLcLSimPmtHitmUgR);
      instance.AdoptCollectionProxyInfo(TCollectionProxyInfo::Generate(TCollectionProxyInfo::Pushback< vector<Tao::SimPmtHit*> >()));

      instance.AdoptAlternate(::ROOT::AddClassAlternate("vector<Tao::SimPmtHit*>","std::vector<Tao::SimPmtHit*, std::allocator<Tao::SimPmtHit*> >"));
      return &instance;
   }
   // Static variable to force the class initialization
   static ::ROOT::TGenericClassInfo *_R__UNIQUE_DICT_(Init) = GenerateInitInstanceLocal(static_cast<const vector<Tao::SimPmtHit*>*>(nullptr)); R__UseDummy(_R__UNIQUE_DICT_(Init));

   // Dictionary for non-ClassDef classes
   static TClass *vectorlETaocLcLSimPmtHitmUgR_Dictionary() {
      TClass* theClass =::ROOT::GenerateInitInstanceLocal(static_cast<const vector<Tao::SimPmtHit*>*>(nullptr))->GetClass();
      vectorlETaocLcLSimPmtHitmUgR_TClassManip(theClass);
   return theClass;
   }

   static void vectorlETaocLcLSimPmtHitmUgR_TClassManip(TClass* ){
   }

} // end of namespace ROOT

namespace ROOT {
   // Wrappers around operator new
   static void *new_vectorlETaocLcLSimPmtHitmUgR(void *p) {
      return  p ? ::new(static_cast<::ROOT::Internal::TOperatorNewHelper*>(p)) vector<Tao::SimPmtHit*> : new vector<Tao::SimPmtHit*>;
   }
   static void *newArray_vectorlETaocLcLSimPmtHitmUgR(Long_t nElements, void *p) {
      return p ? ::new(static_cast<::ROOT::Internal::TOperatorNewHelper*>(p)) vector<Tao::SimPmtHit*>[nElements] : new vector<Tao::SimPmtHit*>[nElements];
   }
   // Wrapper around operator delete
   static void delete_vectorlETaocLcLSimPmtHitmUgR(void *p) {
      delete (static_cast<vector<Tao::SimPmtHit*>*>(p));
   }
   static void deleteArray_vectorlETaocLcLSimPmtHitmUgR(void *p) {
      delete [] (static_cast<vector<Tao::SimPmtHit*>*>(p));
   }
   static void destruct_vectorlETaocLcLSimPmtHitmUgR(void *p) {
      typedef vector<Tao::SimPmtHit*> current_t;
      (static_cast<current_t*>(p))->~current_t();
   }
} // end of namespace ROOT for class vector<Tao::SimPmtHit*>

namespace {
  void TriggerDictionaryInitialization_SimEvtDict_Impl() {
    static const char* headers[] = {
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/DataModel/SimEvent/Event/SimEvt.h",
nullptr
    };
    static const char* includePaths[] = {
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/build/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/Python/3.11.10/include/python3.11",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/Boost/1.85.0",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/log4cpp/1.1.3/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/ROOT/6.30.08/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/CLHEP/2.4.7.1/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J24.2.0/ExternalLibs/CLHEP/2.4.7.1/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/Geant4/10.04.p02.juno/include/geant4",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/HepMC/2.06.11/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/genie/3.04.02/include/GENIE",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/frontier/2.10.2/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/mysql-connector-c/6.1.9/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/mysql-connector-cpp/1.1.12/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/libyaml/0.2.4/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/libonnxruntime/1.17.3/include/onnxruntime",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/libonnxruntime/1.17.3/include/onnxruntime/core/session",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/nuwro/21.09.2/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/DataModel/SimEvent",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/DataModel/SimEvent/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/build/DataModel/SimEvent",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/junosw/InstallArea/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/junosw/InstallArea/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.4.0/ExternalLibs/ROOT/6.30.08/include/",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/build/DataModel/SimEvent/",
nullptr
    };
    static const char* fwdDeclCode = R"DICTFWDDCLS(
#line 1 "SimEvtDict dictionary forward declarations' payload"
#pragma clang diagnostic ignored "-Wkeyword-compat"
#pragma clang diagnostic ignored "-Wignored-attributes"
#pragma clang diagnostic ignored "-Wreturn-type-c-linkage"
extern int __Cling_AutoLoading_Map;
namespace Tao{class __attribute__((annotate("$clingAutoload$/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/DataModel/SimEvent/Event/SimEvt.h")))  SimEvt;}
)DICTFWDDCLS";
    static const char* payloadCode = R"DICTPAYLOAD(
#line 1 "SimEvtDict dictionary payload"


#define _BACKWARD_BACKWARD_WARNING_H
// Inline headers
#include "/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/DataModel/SimEvent/Event/SimEvt.h"

#undef  _BACKWARD_BACKWARD_WARNING_H
)DICTPAYLOAD";
    static const char* classesHeaders[] = {
"Tao::SimEvt", payloadCode, "@",
nullptr
};
    static bool isInitialized = false;
    if (!isInitialized) {
      TROOT::RegisterModule("SimEvtDict",
        headers, includePaths, payloadCode, fwdDeclCode,
        TriggerDictionaryInitialization_SimEvtDict_Impl, {}, classesHeaders, /*hasCxxModule*/false);
      isInitialized = true;
    }
  }
  static struct DictInit {
    DictInit() {
      TriggerDictionaryInitialization_SimEvtDict_Impl();
    }
  } __TheDictionaryInitializer;
}
void TriggerDictionaryInitialization_SimEvtDict() {
  TriggerDictionaryInitialization_SimEvtDict_Impl();
}
